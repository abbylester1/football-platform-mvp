import os
import sys
import cv2
import logging
from config import VIDEOS_DIR, SCENES_DIR, FRAME_INTERVAL
from detection import detect_objects, read_jersey_number, reset_detection
from tracking import track_objects, reset_tracker, merge_close_tracks
from projection import project_to_3d
from calibration import estimate_homography, detect_cones_in_frame
from smoothing import smooth_trajectory
from animation import build_scene
from database import SessionLocal, Drill, DrillStatus

# Ensure logging goes to stdout
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

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
    """Transform normalized crop keypoints to 3D world coordinates."""
    x1, y1, x2, y2 = bbox
    crop_w = x2 - x1
    crop_h = y2 - y1

    world_keypoints = []
    for kp in keypoints:
        px = x1 + kp["x"] * crop_w
        py = y1 + kp["y"] * crop_h
        world = project_to_3d(px, py, homography, frame_width, frame_height)
        world_keypoints.append({
            "x": world["x"],
            "y": world["y"],
            "z": world.get("z", kp.get("z", 0.0)),
            "visibility": kp.get("visibility", 0.0),
        })

    return world_keypoints


def process_drill_sync(drill_id: str, video_path: str) -> str:
    logger.info(f"[{drill_id}] Starting processing pipeline")
    
    if not os.path.exists(video_path):
        logger.error(f"[{drill_id}] Video file not found: {video_path}")
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    logger.info(f"[{drill_id}] Video file exists, size={os.path.getsize(video_path)} bytes")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"[{drill_id}] Failed to open video with cv2")
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    logger.info(f"[{drill_id}] Video info: {total_frames} frames, {frame_width}x{frame_height}, {fps}fps")
    
    frame_count = 0
    processed_count = 0
    all_detections = []
    all_cone_bboxes: list[tuple[float, float, float, float]] = []
    reset_tracker()
    reset_detection()

    logger.info(f"[{drill_id}] Starting frame-by-frame detection (interval={FRAME_INTERVAL})")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % FRAME_INTERVAL != 0:
            continue

        processed_count += 1
        if processed_count % 10 == 0:
            logger.info(f"[{drill_id}] Processed {processed_count} keyframes ({frame_count}/{total_frames} frames)")

        detections = detect_objects(frame)
        tracked = track_objects(detections, frame_count)

        for obj in tracked:
            x1, y1, x2, y2 = obj["bbox"]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            obj["center"] = (cx, cy)
            obj["frame_idx"] = frame_count

        all_detections.extend(tracked)

        for det in detections:
            if det.get("keypoints"):
                for tracked_obj in tracked:
                    if tracked_obj["type"] == det["type"]:
                        tb = tracked_obj["bbox"]
                        db = det["bbox"]
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
    logger.info(f"[{drill_id}] Detection complete: {processed_count} keyframes, {len(all_detections)} detections")

    objects_by_id: dict[int, list] = {}
    for det in all_detections:
        tid = det.get("track_id")
        if tid is None:
            continue
        objects_by_id.setdefault(tid, []).append(det)
    logger.info(f"[{drill_id}] Raw tracks: {len(objects_by_id)} unique objects")

    # Merge close tracks (same type, overlapping spatial positions)
    objects_by_id = merge_close_tracks(objects_by_id, max_center_dist=3.0)
    logger.info(f"[{drill_id}] After merge: {len(objects_by_id)} objects")

    # Filter out short tracks (< 3 frames) — these are ghosts
    min_track_length = 3
    objects_by_id = {tid: dets for tid, dets in objects_by_id.items() if len(dets) >= min_track_length}
    logger.info(f"[{drill_id}] After filtering (< {min_track_length} frames): {len(objects_by_id)} objects")

    # Cap total objects: at most 25 players (22 on field + subs) and 5 balls/cones
    players = {tid: dets for tid, dets in objects_by_id.items() if dets[0]["type"] == "player"}
    non_players = {tid: dets for tid, dets in objects_by_id.items() if dets[0]["type"] != "player"}
    if len(players) > 25:
        # Keep players with most detections (most tracked)
        sorted_pids = sorted(players.keys(), key=lambda tid: len(players[tid]), reverse=True)
        players = {tid: players[tid] for tid in sorted_pids[:25]}
        logger.info(f"[{drill_id}] Capped players from {len(sorted_pids)} to 25")
    if len(non_players) > 10:
        sorted_nids = sorted(non_players.keys(), key=lambda tid: len(non_players[tid]), reverse=True)
        non_players = {tid: non_players[tid] for tid in sorted_nids[:10]}
    objects_by_id = {**players, **non_players}
    logger.info(f"[{drill_id}] Final: {len(objects_by_id)} objects ({len(players)} players, {len(non_players)} non-players)")

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
    logger.info(f"[{drill_id}] Homography: {'estimated' if homography is not None else 'none (using fallback)'}")

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

            if det.get("keypoints"):
                keypoints_3d = project_keypoints_to_3d(
                    det["keypoints"], det["bbox"], homography, frame_width, frame_height
                )
                frame_data["keypoints"] = keypoints_3d

            frames.append(frame_data)

        positions = [(f["x"], f["y"], f["z"]) for f in frames]
        smoothed = smooth_trajectory(positions)
        for i, f in enumerate(frames):
            f["x"], f["y"], f["z"] = smoothed[i]

        if POSE_ENABLED and _smooth_keypoints and obj_type == "player" and any(f.get("keypoints") for f in frames):
            frames = _smooth_keypoints(frames)

        detected_objects_list.append({
            "type": obj_type,
            "id": f"{obj_type}_{tid}",
            "label": label if obj_type != "player" else dets[0].get("label", label),
            "frames": frames,
        })

    logger.info(f"[{drill_id}] Building 3D scene...")
    scene_path = build_scene(detected_objects_list, drill_id, SCENES_DIR)
    logger.info(f"[{drill_id}] Scene built: {scene_path}")

    db = SessionLocal()
    try:
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if drill:
            drill.detected_objects = detected_objects_list
            drill.scene_key = os.path.basename(scene_path)
            drill.status = DrillStatus.REVIEW.value
            db.commit()
            logger.info(f"[{drill_id}] Drill saved with status REVIEW")
    finally:
        db.close()

    return os.path.basename(scene_path)
