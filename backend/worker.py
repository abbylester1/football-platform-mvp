import os
import cv2
from config import VIDEOS_DIR, SCENES_DIR, FRAME_INTERVAL
from detection import detect_objects, read_jersey_number, reset_detection
from tracking import track_objects, reset_tracker
from projection import project_to_3d
from calibration import estimate_homography, detect_cones_in_frame
from smoothing import smooth_trajectory
from animation import build_scene
from database import SessionLocal, Drill, DrillStatus
import os

POSE_ENABLED = os.environ.get("POSE_ESTIMATION_ENABLED", "true").lower() == "true"

# Lazy import for keypoint smoothing
_smooth_keypoints = None
if POSE_ENABLED:
    try:
        from smoothing import smooth_keypoints as _smooth_keypoints
    except Exception:
        pass


def project_keypoints_to_3d(
    keypoints: list[dict],
    bbox: list[float],
    homography,
    frame_width: int,
    frame_height: int,
) -> list[dict]:
    """Transform normalized crop keypoints to 3D world coordinates.

    Converts normalized crop-relative keypoints (0-1) to full-frame pixel
    coordinates, then applies the homography to get pitch-world coordinates.

    Args:
        keypoints: List of {x, y, z, visibility} normalized to crop bbox.
        bbox: [x1, y1, x2, y2] in pixel coordinates.
        homography: 3x3 homography matrix (or None for linear fallback).
        frame_width: Video frame width in pixels.
        frame_height: Video frame height in pixels.

    Returns:
        List of {x, y, z, visibility} in world coordinates.
    """
    x1, y1, x2, y2 = bbox
    crop_w = x2 - x1
    crop_h = y2 - y1

    world_keypoints = []
    for kp in keypoints:
        # Scale normalized crop coords to full-frame pixel coords
        px = x1 + kp["x"] * crop_w
        py = y1 + kp["y"] * crop_h

        # Apply homography to get world coordinates
        world = project_to_3d(px, py, homography, frame_width, frame_height)

        world_keypoints.append({
            "x": world["x"],
            "y": world["y"],
            "z": world.get("z", kp.get("z", 0.0)),
            "visibility": kp.get("visibility", 0.0),
        })

    return world_keypoints


import logging

logger = logging.getLogger(__name__)


def process_drill_sync(drill_id: str, video_path: str) -> str:
    logger.info(f"Starting processing for drill {drill_id}")
    try:
        cap = cv2.VideoCapture(video_path)
    except Exception as e:
        logger.error(f"Failed to open video: {e}")
        raise
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info(f"Video: {total_frames} frames, {frame_width}x{frame_height}")
    frame_count = 0
    all_detections = []
    all_cone_bboxes: list[tuple[float, float, float, float]] = []
    reset_tracker()
    reset_detection()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % FRAME_INTERVAL != 0:
            continue

        detections = detect_objects(frame)
        tracked = track_objects(detections, frame_count)

        for obj in tracked:
            x1, y1, x2, y2 = obj["bbox"]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            obj["center"] = (cx, cy)
            obj["frame_idx"] = frame_count

        all_detections.extend(tracked)

        # Store keypoints from detection for later use in pipeline
        for det in detections:
            if det.get("keypoints"):
                # Match detection to tracked object by bbox overlap
                for tracked_obj in tracked:
                    if tracked_obj["type"] == det["type"]:
                        tb = tracked_obj["bbox"]
                        db = det["bbox"]
                        # Simple overlap check — if bboxes overlap significantly
                        ix1 = max(tb[0], db[0])
                        iy1 = max(tb[1], db[1])
                        ix2 = min(tb[2], db[2])
                        iy2 = min(tb[3], db[3])
                        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                        area_a = (tb[2] - tb[0]) * (tb[3] - tb[1])
                        if area_a > 0 and inter / area_a > 0.5:
                            tracked_obj["keypoints"] = det["keypoints"]
                            break

        for obj in tracked:
            if obj["type"] == "player" and "label" not in obj:
                number = read_jersey_number(frame, obj["bbox"])
                if number:
                    obj["label"] = number

        cones = detect_cones_in_frame(frame)
        all_cone_bboxes.extend(cones)

    cap.release()
    logger.info(f"Processed {frame_count} frames, found {len(all_detections)} detections")

    objects_by_id: dict[int, list] = {}
    for det in all_detections:
        tid = det.get("track_id")
        if tid is None:
            continue
        objects_by_id.setdefault(tid, []).append(det)
    logger.info(f"Tracked {len(objects_by_id)} unique objects")

    cone_positions_2d = []
    for tid, dets in objects_by_id.items():
        if dets[0]["type"] == "cone":
            cone_positions_2d.extend([d["center"] for d in dets])

    if not cone_positions_2d and all_cone_bboxes:
        for x1, y1, x2, y2 in all_cone_bboxes:
            cone_positions_2d.append(((x1 + x2) / 2, (y1 + y2) / 2))

    homography = None
    if len(cone_positions_2d) >= 4:
        homography = estimate_homography(cone_positions_2d[:4])

    detected_objects_list = []
    for tid, dets in objects_by_id.items():
        obj_type = dets[0]["type"]
        label = dets[0].get("type", "")
        frames = []
        for det in dets:
            cx, cy = det["center"]
            x3d, y3d, z3d = project_to_3d(cx, cy, homography, frame_width, frame_height)

            frame_data = {
                "frame": det["frame_idx"],
                "x": float(x3d),
                "y": float(y3d),
                "z": float(z3d),
            }

            # Project keypoints to 3D if available
            if det.get("keypoints"):
                keypoints_3d = project_keypoints_to_3d(
                    det["keypoints"], det["bbox"], homography, frame_width, frame_height
                )
                frame_data["keypoints"] = keypoints_3d

            frames.append(frame_data)

        # Smooth center trajectory
        positions = [(f["x"], f["y"], f["z"]) for f in frames]
        smoothed = smooth_trajectory(positions)
        for i, f in enumerate(frames):
            f["x"], f["y"], f["z"] = smoothed[i]

        # Smooth keypoints trajectories
        if POSE_ENABLED and _smooth_keypoints and obj_type == "player" and any(f.get("keypoints") for f in frames):
            frames = _smooth_keypoints(frames)

        detected_objects_list.append({
            "type": obj_type,
            "id": f"{obj_type}_{tid}",
            "label": label if obj_type != "player" else dets[0].get("label", label),
            "frames": frames,
        })

    scene_path = build_scene(detected_objects_list, drill_id, SCENES_DIR)

    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if drill:
            drill.detected_objects = detected_objects_list
            drill.scene_key = os.path.basename(scene_path)
            drill.status = DrillStatus.REVIEW.value
            db.commit()
    finally:
        db.close()

    return os.path.basename(scene_path)
