import cv2
import pytesseract
import onnxruntime
import numpy as np
from typing import Optional, List, Dict
from config import YOLO_MODEL, DETECTION_CONFIDENCE

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

    def __init__(self, history: int = 50, var_threshold: float = 16.0, min_area: int = 30):
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

    if yolo_detections:
        return yolo_detections

    global _motion_detector
    if _motion_detector is None:
        _motion_detector = MotionDetector()
    return _motion_detector.detect(frame)


def reset_motion_detector():
    global _motion_detector
    _motion_detector = None
