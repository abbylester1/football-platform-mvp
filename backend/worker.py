import os
import cv2
from config import VIDEOS_DIR, SCENES_DIR, FRAME_INTERVAL
from detection import detect_objects
from tracking import track_objects, reset_tracker
from projection import project_to_3d
from calibration import estimate_homography
from smoothing import smooth_trajectory
from animation import build_scene
from database import SessionLocal, Drill, DrillStatus


def process_drill_sync(drill_id: str, video_path: str) -> str:
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    all_detections = []
    reset_tracker()

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

    cap.release()

    objects_by_id: dict[int, list] = {}
    for det in all_detections:
        tid = det.get("track_id")
        if tid is None:
            continue
        objects_by_id.setdefault(tid, []).append(det)

    cone_positions_2d = []
    for tid, dets in objects_by_id.items():
        if dets[0]["type"] == "cone":
            cone_positions_2d.extend([d["center"] for d in dets])

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
            x3d, y3d, z3d = project_to_3d(cx, cy, homography)
            frames.append({
                "frame": det["frame_idx"],
                "x": float(x3d),
                "y": float(y3d),
                "z": float(z3d),
            })

        positions = [(f["x"], f["y"], f["z"]) for f in frames]
        smoothed = smooth_trajectory(positions)
        for i, f in enumerate(frames):
            f["x"], f["y"], f["z"] = smoothed[i]

        detected_objects_list.append({
            "type": obj_type,
            "id": f"{obj_type}_{tid}",
            "label": label,
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
