import cv2
import numpy as np

CONE_COLOR_RANGES = [
    # Yellow cones
    ((20, 80, 80), (35, 255, 255)),      # Pure yellow
    ((15, 60, 120), (40, 255, 255)),     # Yellow-orange (wider)
    # Pink/red cones
    ((140, 50, 80), (175, 255, 255)),    # Pink/magenta
    ((0, 50, 100), (10, 255, 255)),      # Red (low hue)
    ((165, 50, 80), (180, 255, 255)),    # Red (high hue, wraps)
    # Orange cones (backup)
    ((5, 80, 80), (20, 255, 255)),       # Standard orange
    ((0, 100, 150), (15, 255, 255)),     # Bright orange
]

def estimate_homography(cone_positions: list[tuple[float, float]], field_width: float = 105.0, field_height: float = 68.0):
    if len(cone_positions) < 4:
        return None
    src_pts = np.array(cone_positions, dtype=np.float32).reshape(-1, 1, 2)
    dst_pts = _estimate_field_points(len(cone_positions), field_width, field_height)
    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    return H

def point_in_drill_area(px: float, py: float, drill_polygon: np.ndarray) -> bool:
    """Check if a point (px, py) is inside the convex drill area polygon."""
    if drill_polygon is None or len(drill_polygon) < 3:
        return True  # No polygon = accept all
    pt = np.array([[px, py]], dtype=np.float32)
    return cv2.pointPolygonTest(drill_polygon, (float(px), float(py)), False) >= 0

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
    min_area: int = 20,
    max_area: int = 20000,
) -> list[tuple[float, float, float, float]]:
    """Detect orange/yellow cones on the field. Wider range for varied lighting."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for low, high in CONE_COLOR_RANGES:
        mask |= cv2.inRange(hsv, np.array(low, dtype=np.uint8), np.array(high, dtype=np.uint8))

    # Clean up noise
    kernel_small = np.ones((3, 3), np.uint8)
    kernel_large = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)

    # Also look for bright saturated objects (cones are often very bright)
    # Yellow-orange range
    bright_mask1 = cv2.inRange(hsv, np.array([15, 100, 150], dtype=np.uint8),
                                   np.array([35, 255, 255], dtype=np.uint8))
    # Pink/magenta range
    bright_mask2 = cv2.inRange(hsv, np.array([140, 100, 150], dtype=np.uint8),
                                   np.array([175, 255, 255], dtype=np.uint8))
    # Red range
    bright_mask3 = cv2.inRange(hsv, np.array([0, 100, 150], dtype=np.uint8),
                                   np.array([10, 255, 255], dtype=np.uint8))
    mask = cv2.bitwise_or(mask, bright_mask1)
    mask = cv2.bitwise_or(mask, bright_mask2)
    mask = cv2.bitwise_or(mask, bright_mask3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_small, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cones = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h
        # Cones are roughly square or taller than wide (overhead view)
        if aspect < 0.2 or aspect > 3.0:
            continue
        cones.append((float(x), float(y), float(x + w), float(y + h)))
    return cones
