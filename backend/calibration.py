import cv2
import numpy as np

def estimate_homography(cone_positions: list[tuple[float, float]], field_width: float = 105.0, field_height: float = 68.0):
    if len(cone_positions) < 4:
        return None
    src_pts = np.array(cone_positions, dtype=np.float32).reshape(-1, 1, 2)
    dst_pts = _estimate_field_points(len(cone_positions), field_width, field_height)
    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    return H

def _estimate_field_points(n: int, fw: float, fh: float) -> np.ndarray:
    if n == 4:
        return np.array([[0, 0], [fw, 0], [fw, fh], [0, fh]], dtype=np.float32).reshape(-1, 1, 2)
    pts = []
    perimeter = 2 * (fw + fh)
    for i in range(n):
        t = (i / n) * perimeter
        if t < fw:
            pts.append([t, 0])
        elif t < fw + fh:
            pts.append([fw, t - fw])
        elif t < 2 * fw + fh:
            pts.append([2 * fw + fh - t, fh])
        else:
            pts.append([0, perimeter - t])
    return np.array(pts, dtype=np.float32).reshape(-1, 1, 2)

def detect_cones_in_frame(frame: np.ndarray):
    return []  # Placeholder: color-based cone detection
