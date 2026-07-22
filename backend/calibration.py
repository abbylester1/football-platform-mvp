import cv2
import numpy as np

CONE_COLOR_RANGES = [
    ((5, 80, 80), (20, 255, 255)),
]

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

def detect_cones_in_frame(
    frame: np.ndarray,
    min_area: int = 50,
    max_area: int = 5000,
) -> list[tuple[float, float, float, float]]:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for low, high in CONE_COLOR_RANGES:
        mask |= cv2.inRange(hsv, np.array(low, dtype=np.uint8), np.array(high, dtype=np.uint8))

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cones = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h
        if aspect < 0.3 or aspect > 2.0:
            continue
        cones.append((float(x), float(y), float(x + w), float(y + h)))
    return cones
