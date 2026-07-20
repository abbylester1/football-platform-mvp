import cv2
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

def detect_objects(frame: Optional[np.ndarray], confidence_threshold: float = DETECTION_CONFIDENCE) -> List[Dict]:
    if frame is None:
        return []
    session = _get_session()
    input_tensor = _preprocess(frame)
    outputs = session.run(None, {_input_name: input_tensor})
    return _postprocess(outputs, confidence_threshold, frame.shape[:2])
