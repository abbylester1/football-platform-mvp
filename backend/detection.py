from ultralytics import YOLO
import numpy as np
from typing import Optional, List, Dict
from backend.config import YOLO_MODEL, DETECTION_CONFIDENCE

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = YOLO(YOLO_MODEL)
    return _model

COCO_CLASS_MAP = {
    0: "player",
    32: "ball",
}

def detect_objects(frame: Optional[np.ndarray], confidence_threshold: float = DETECTION_CONFIDENCE) -> List[Dict]:
    if frame is None:
        return []

    model = _get_model()
    results = model(frame, conf=confidence_threshold, verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            mapped_type = COCO_CLASS_MAP.get(cls_id)
            if mapped_type is None:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            detections.append({
                "type": mapped_type,
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
            })

    return detections
