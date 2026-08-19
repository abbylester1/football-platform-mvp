import cv2
import pytesseract
import onnxruntime
import numpy as np
from typing import Optional, List, Dict
from config import YOLO_MODEL, DETECTION_CONFIDENCE
import os

# Pose estimation can be disabled via environment variable
POSE_ENABLED = os.environ.get("POSE_ESTIMATION_ENABLED", "true").lower() == "true"

# Lazy import to handle environments where pose_estimation might fail
_extract_pose_keypoints = None
_pose_checked = False


def _get_pose_extractor():
    """Lazy import of pose estimation to avoid import-time failures."""
    global _extract_pose_keypoints, _pose_checked
    if _pose_checked:
        return _extract_pose_keypoints
    _pose_checked = True
    if not POSE_ENABLED:
        return None
    try:
        from pose_estimation import extract_pose_keypoints
        _extract_pose_keypoints = extract_pose_keypoints
        return _extract_pose_keypoints
    except Exception:
        return None

_session = None
_input_name = None

def _get_session():
    global _session, _input_name
    if _session is None:
        onnx_path = YOLO_MODEL.replace(".pt", ".onnx")
        _session = onnxruntime.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        _input_name = _session.get_inputs()[0].name
    return _session

COCO_CLASS_MAP = {
    0: "player",
    32: "ball",
}

def _preprocess(frame: np.ndarray) -> np.ndarray:
    img = cv2.resize(frame, (640, 640))
    img = img[:, :, ::-1].transpose(2, 0, 1)
    img = np.ascontiguousarray(img).astype(np.float32) / 255.0
    return np.expand_dims(img, axis=0)

def _nms(detections: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
    """Non-Maximum Suppression: remove overlapping boxes of the same type.
    
    Keeps the highest-confidence detection when two boxes overlap beyond
    the iou_threshold. Applied separately per object type (players, balls, cones).
    """
    if not detections:
        return detections

    # Group by type
    by_type: Dict[str, List[Dict]] = {}
    for d in detections:
        by_type.setdefault(d["type"], []).append(d)

    result = []
    for obj_type, dets in by_type.items():
        # Sort by confidence descending
        dets.sort(key=lambda d: d["confidence"], reverse=True)
        keep = []
        suppressed = set()
        for i, d in enumerate(dets):
            if i in suppressed:
                continue
            keep.append(d)
            for j in range(i + 1, len(dets)):
                if j in suppressed:
                    continue
                # Compute IoU
                bi, bj = d["bbox"], dets[j]["bbox"]
                ix1 = max(bi[0], bj[0])
                iy1 = max(bi[1], bj[1])
                ix2 = min(bi[2], bj[2])
                iy2 = min(bi[3], bj[3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area_i = (bi[2] - bi[0]) * (bi[3] - bi[1])
                area_j = (bj[2] - bj[0]) * (bj[3] - bj[1])
                union = area_i + area_j - inter
                iou_val = inter / union if union > 0 else 0.0
                if iou_val > iou_threshold:
                    suppressed.add(j)
        result.extend(keep)
    return result


def _postprocess(outputs: np.ndarray, confidence_threshold: float, orig_shape: tuple) -> List[Dict]:
    arr = outputs[0][0]
    boxes = arr[:4, :].T
    scores = arr[4:, :].T
    detections = []
    for i in range(scores.shape[0]):
        max_score = scores[i].max()
        if max_score < confidence_threshold:
            continue
        cls_id = int(scores[i].argmax())
        mapped_type = COCO_CLASS_MAP.get(cls_id)
        if mapped_type is None:
            continue
        x, y, w, h = boxes[i]
        x1 = (x - w / 2) * orig_shape[1] / 640
        y1 = (y - h / 2) * orig_shape[0] / 640
        x2 = (x + w / 2) * orig_shape[1] / 640
        y2 = (y + h / 2) * orig_shape[0] / 640
        detections.append({
            "type": mapped_type,
            "bbox": [x1, y1, x2, y2],
            "confidence": float(max_score),
        })
    # Apply NMS to remove overlapping duplicates
    detections = _nms(detections, iou_threshold=0.5)
    return detections

def read_jersey_number(frame: np.ndarray, bbox: list[float]) -> str:
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h = y2 - y1
    crop_top = y1
    crop_bot = y1 + int(h * 0.35)
    crop_left = max(0, x1)
    crop_right = min(frame.shape[1], x2)
    if crop_bot <= crop_top or crop_right <= crop_left:
        return ""
    roi = frame[crop_top:crop_bot, crop_left:crop_right]
    if roi.size == 0:
        return ""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    config = "--psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(thresh, config=config).strip()
    return text


class MotionDetector:
    """Background subtraction detector for aerial/overhead sports footage.

    When YOLO fails (players too small for the model), this uses
    background subtraction to find moving blobs on the field.
    """

    def __init__(self, history: int = 50, var_threshold: float = 16.0, min_area: int = 200):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=var_threshold, detectShadows=False
        )
        self.min_area = min_area
        self._initialized = False

    def detect(self, frame: np.ndarray) -> List[Dict]:
        mask = self.bg_subtractor.apply(frame)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        mask = cv2.dilate(mask, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / h if h > 0 else 0
            if aspect < 0.2 or aspect > 5.0:
                continue

            obj_type = self._classify_blob(frame, x, y, w, h, area)
            cx, cy = x + w / 2, y + h / 2
            detections.append({
                "type": obj_type,
                "bbox": [float(x), float(y), float(x + w), float(y + h)],
                "confidence": min(1.0, area / 200.0),
            })
        return detections

    def _classify_blob(self, frame: np.ndarray, x: int, y: int, w: int, h: int, area: float) -> str:
        roi = frame[y:y + h, x:x + w]
        if roi.size == 0:
            return "player"
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_h, mean_s, mean_v = cv2.mean(hsv)[:3]
        white_mask = cv2.inRange(hsv, (0, 0, 180), (180, 40, 255))
        white_ratio = (white_mask > 0).sum() / max(roi.shape[0] * roi.shape[1], 1)
        if white_ratio > 0.5 and area < 150:
            return "ball"
        orange_mask = cv2.inRange(hsv, (5, 80, 80), (20, 255, 255))
        orange_ratio = (orange_mask > 0).sum() / max(roi.shape[0] * roi.shape[1], 1)
        if orange_ratio > 0.6:
            return "cone"
        return "player"


_motion_detector: Optional[MotionDetector] = None


def detect_objects(frame: Optional[np.ndarray], confidence_threshold: float = DETECTION_CONFIDENCE) -> List[Dict]:
    if frame is None:
        return []

    session = _get_session()
    input_tensor = _preprocess(frame)
    outputs = session.run(None, {_input_name: input_tensor})
    yolo_detections = _postprocess(outputs, confidence_threshold, frame.shape[:2])

    if not yolo_detections:
        global _motion_detector
        if _motion_detector is None:
            _motion_detector = MotionDetector()
        motion_dets = _motion_detector.detect(frame)
        # Only use motion detections with reasonable confidence
        yolo_detections = [d for d in motion_dets if d.get("confidence", 0) > 0.3]
        # Apply NMS to motion detections too
        yolo_detections = _nms(yolo_detections, iou_threshold=0.4)

    # Cap player detections to a reasonable max (football has at most ~22 players)
    players = [d for d in yolo_detections if d["type"] == "player"]
    others = [d for d in yolo_detections if d["type"] != "player"]
    if len(players) > 30:
        # Keep only the 30 highest-confidence player detections
        players.sort(key=lambda d: d["confidence"], reverse=True)
        players = players[:30]
    yolo_detections = players + others

    # Extract pose keypoints for each detected player (if enabled)
    if POSE_ENABLED:
        pose_extractor = _get_pose_extractor()
        if pose_extractor:
            for det in yolo_detections:
                if det["type"] == "player":
                    try:
                        keypoints = pose_extractor(frame, tuple(det["bbox"]))
                        det["keypoints"] = keypoints  # None if pose detection fails
                    except Exception:
                        det["keypoints"] = None

    return yolo_detections


def reset_motion_detector():
    global _motion_detector
    _motion_detector = None


def reset_detection():
    """Reset all detection state (motion detector + pose estimator)."""
    reset_motion_detector()
    if POSE_ENABLED:
        try:
            from pose_estimation import reset_pose
            reset_pose()
        except Exception:
            pass
