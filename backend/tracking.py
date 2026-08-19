import numpy as np
from scipy.optimize import linear_sum_assignment


class _TrackerState:
    def __init__(self):
        self.next_id = 1
        self.active_tracks: dict[int, dict] = {}
        self.max_disappeared = 5  # Remove tracks lost for 5+ frames

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


def _center_distance(box_a: list[float], box_b: list[float]) -> float:
    """Euclidean distance between box centers, normalized by average box diagonal."""
    cx_a = (box_a[0] + box_a[2]) / 2
    cy_a = (box_a[1] + box_a[3]) / 2
    cx_b = (box_b[0] + box_b[2]) / 2
    cy_b = (box_b[1] + box_b[3]) / 2
    dist = np.sqrt((cx_a - cx_b) ** 2 + (cy_a - cy_b) ** 2)
    # Normalize by average diagonal size
    diag_a = np.sqrt((box_a[2] - box_a[0]) ** 2 + (box_a[3] - box_a[1]) ** 2)
    diag_b = np.sqrt((box_b[2] - box_b[0]) ** 2 + (box_b[3] - box_b[1]) ** 2)
    avg_diag = (diag_a + diag_b) / 2
    return dist / avg_diag if avg_diag > 0 else 999.0


def _match_cost(track_box: list[float], det_box: list[float]) -> float:
    """Combined matching cost using IoU and center distance.
    
    Returns 0.0 for perfect match, up to 1.0+ for poor match.
    A cost < 0.6 is considered a valid match (much more lenient than pure IoU).
    """
    iou_val = _iou(track_box, det_box)
    cdist = _center_distance(track_box, det_box)
    
    # IoU component: 1 - IoU (0 for perfect overlap)
    iou_cost = 1.0 - iou_val
    # Distance component: cap at 1.0
    dist_cost = min(cdist, 1.0)
    
    # Weighted combination: favor IoU but allow distance to break ties
    return 0.6 * iou_cost + 0.4 * dist_cost


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

    # Build cost matrix using combined IoU + center distance
    cost = np.ones((len(track_boxes), len(det_boxes)))
    for i, tb in enumerate(track_boxes):
        for j, db in enumerate(det_boxes):
            cost[i, j] = _match_cost(tb, db)

    row_idx, col_idx = linear_sum_assignment(cost)
    matched_dets = set()
    matched_tracks = set()

    for r, c in zip(row_idx, col_idx):
        # More lenient threshold: cost < 0.6 means decent IoU or close center
        if cost[r, c] < 0.6:
            tid = track_keys[r]
            _tracker.active_tracks[tid] = {
                **detections[c],
                "track_id": tid,
                "disappeared": 0,
            }
            matched_tracks.add(tid)
            matched_dets.add(c)

    # Create new tracks only for truly unmatched detections
    for j in range(len(detections)):
        if j not in matched_dets:
            tid = _tracker.next_id
            _tracker.next_id += 1
            _tracker.active_tracks[tid] = {**detections[j], "track_id": tid, "disappeared": 0}

    # Age out unmatched tracks
    for tid in list(_tracker.active_tracks.keys()):
        if tid not in matched_tracks:
            _tracker.active_tracks[tid]["disappeared"] += 1
            if _tracker.active_tracks[tid]["disappeared"] > _tracker.max_disappeared:
                del _tracker.active_tracks[tid]

    return list(_tracker.active_tracks.values())


def merge_close_tracks(detections_by_id: dict[int, list], max_center_dist: float = 2.0) -> dict[int, list]:
    """Post-processing: merge tracks that are very close in space.
    
    Two tracks of the same type are merged if their average center positions
    are within max_center_dist (in normalized frame coords).
    """
    if not detections_by_id:
        return detections_by_id

    def _avg_center(dets):
        xs = [d["center"][0] for d in dets if "center" in d]
        ys = [d["center"][1] for d in dets if "center" in d]
        return (np.mean(xs), np.mean(ys)) if xs else (0, 0)

    track_ids = list(detections_by_id.keys())
    track_centers = {}
    track_types = {}
    for tid in track_ids:
        dets = detections_by_id[tid]
        track_centers[tid] = _avg_center(dets)
        track_types[tid] = dets[0]["type"]

    # Find pairs to merge
    merge_map = {}  # tid -> tid_to_merge_into
    for i, tid_a in enumerate(track_ids):
        if tid_a in merge_map:
            continue
        cx_a, cy_a = track_centers[tid_a]
        for tid_b in track_ids[i + 1:]:
            if tid_b in merge_map:
                continue
            if track_types[tid_a] != track_types[tid_b]:
                continue
            cx_b, cy_b = track_centers[tid_b]
            dist = np.sqrt((cx_a - cx_b) ** 2 + (cy_a - cy_b) ** 2)
            if dist < max_center_dist:
                # Merge the shorter track into the longer one
                len_a = len(detections_by_id[tid_a])
                len_b = len(detections_by_id[tid_b])
                if len_a >= len_b:
                    merge_map[tid_b] = tid_a
                else:
                    merge_map[tid_a] = tid_b
                    break

    # Apply merges
    merged = {}
    for tid, dets in detections_by_id.items():
        if tid in merge_map:
            target = merge_map[tid]
            # Ensure target exists in merged
            if target not in merged:
                target_dets = detections_by_id.get(target, [])
                merged[target] = list(target_dets)
            # Add this track's detections, avoiding duplicate frames
            existing_frames = {d["frame_idx"] for d in merged[target]}
            for d in dets:
                if d["frame_idx"] not in existing_frames:
                    merged[target].append(d)
                    existing_frames.add(d["frame_idx"])
        else:
            if tid not in merged:
                merged[tid] = list(dets)

    # Re-sort each track by frame
    for tid in merged:
        merged[tid].sort(key=lambda d: d["frame_idx"])

    return merged


def reset_tracker():
    _tracker.reset()
