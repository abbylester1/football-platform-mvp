import numpy as np
from scipy.optimize import linear_sum_assignment


class _TrackerState:
    def __init__(self):
        self.next_id = 1
        self.active_tracks: dict[int, dict] = {}
        self.max_disappeared = 10

    def reset(self):
        self.next_id = 1
        self.active_tracks.clear()


_tracker = _TrackerState()


def _iou(box_a: list[float], box_b: list[float]) -> float:
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def track_objects(detections: list[dict], frame_idx: int) -> list[dict]:
    if not detections:
        for tid in list(_tracker.active_tracks.keys()):
            _tracker.active_tracks[tid]["disappeared"] += 1
            if _tracker.active_tracks[tid]["disappeared"] > _tracker.max_disappeared:
                del _tracker.active_tracks[tid]
        return []

    if not _tracker.active_tracks:
        for d in detections:
            tid = _tracker.next_id
            _tracker.next_id += 1
            _tracker.active_tracks[tid] = {**d, "disappeared": 0, "track_id": tid}
        return list(_tracker.active_tracks.values())

    track_keys = list(_tracker.active_tracks.keys())
    track_boxes = [_tracker.active_tracks[tid]["bbox"] for tid in track_keys]
    det_boxes = [d["bbox"] for d in detections]

    cost = np.ones((len(track_boxes), len(det_boxes)))
    for i, tb in enumerate(track_boxes):
        for j, db in enumerate(det_boxes):
            cost[i, j] = 1.0 - _iou(tb, db)

    row_idx, col_idx = linear_sum_assignment(cost)
    matched_dets = set()
    matched_tracks = set()

    for r, c in zip(row_idx, col_idx):
        if cost[r, c] < 0.7:
            tid = track_keys[r]
            _tracker.active_tracks[tid] = {
                **detections[c],
                "track_id": tid,
                "disappeared": 0,
            }
            matched_tracks.add(tid)
            matched_dets.add(c)

    for j in range(len(detections)):
        if j not in matched_dets:
            tid = _tracker.next_id
            _tracker.next_id += 1
            _tracker.active_tracks[tid] = {**detections[j], "track_id": tid, "disappeared": 0}

    for tid in list(_tracker.active_tracks.keys()):
        if tid not in matched_tracks:
            _tracker.active_tracks[tid]["disappeared"] += 1
            if _tracker.active_tracks[tid]["disappeared"] > _tracker.max_disappeared:
                del _tracker.active_tracks[tid]

    return list(_tracker.active_tracks.values())


def reset_tracker():
    _tracker.reset()
