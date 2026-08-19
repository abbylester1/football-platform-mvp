"""Player/ball detection using Ultralytics YOLO.

Uses the official ultralytics library for correct preprocessing (letterboxing),
DFL bbox decoding, and NMS — eliminating all manual ONNX postprocessing bugs.

Model: YOLO11s (small) for better accuracy on distant/small players in sports video.
Also supports YOLO11-pose for joint keypoint extraction in a single forward pass.
"""

import os
import logging
import cv2
import numpy as np
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Pose estimation can be disabled via environment variable
POSE_ENABLED = os.environ.get("POSE_ESTIMATION_ENABLED", "true").lower() == "true"

# Lazy-loaded YOLO models (singleton)
_detect_model = None
_pose_model = None


def _get_detect_model():
    """Load YOLO detection model (lazy singleton)."""
    global _detect_model
    if _detect_model is not None:
        return _detect_model

    try:
        from ultralytics import YOLO

        # Try yolo11s.pt first (better accuracy), fall back to yolo11n.pt
        model_path = os.environ.get("YOLO_DETECT_MODEL", "yolo11s.pt")
        if not os.path.exists(model_path):
            model_path = "yolo11n.pt"

        logger.info(f"[detect] Loading YOLO detection model: {model_path}")
        _detect_model = YOLO(model_path)
        logger.info(f"[detect] Detection model loaded: {_detect_model.model_name if hasattr(_detect_model, 'model_name') else model_path}")
        return _detect_model
    except ImportError:
        logger.error("[detect] ultralytics not installed! pip install ultralytics")
        raise
    except Exception as e:
        logger.error(f"[detect] Failed to load YOLO model: {e}")
        raise


def _get_pose_model():
    """Load YOLO pose model (lazy singleton). Returns None if not available."""
    global _pose_model
    if _pose_model is not None:
        return _pose_model
    if not POSE_ENABLED:
        return None

    try:
        from ultralytics import YOLO

        model_path = os.environ.get("YOLO_POSE_MODEL", "yolo11s-pose.pt")
        if not os.path.exists(model_path):
            model_path = "yolo11n-pose.pt"

        logger.info(f"[pose] Loading YOLO pose model: {model_path}")
        _pose_model = YOLO(model_path)
        logger.info(f"[pose] Pose model loaded")
        return _pose_model
    except Exception as e:
        logger.warning(f"[pose] Failed to load pose model: {e}. Pose estimation disabled.")
        return None


# COCO class mapping for our use case
# Class 0 = person, Class 32 = sports ball
COCO_CLASSES = {
    0: "player",
    32: "ball",
}

# Additional classes we want to detect (sports-related)
DETECT_CLASSES = [0, 32]  # person, sports ball


def detect_objects(
    frame: Optional[np.ndarray],
    confidence_threshold: float = 0.25,
    img_size: int = 640,
) -> List[Dict]:
    """Detect players, balls, and other objects in a frame using YOLO.

    Args:
        frame: BGR image (H, W, 3)
        confidence_threshold: Minimum detection confidence (0-1)
        img_size: Input image size for the model

    Returns:
        List of detection dicts with keys: type, bbox, confidence, keypoints
    """
    if frame is None:
        return []

    model = _get_detect_model()

    try:
        # Run inference with ultralytics — handles letterboxing, DFL, NMS internally
        # Detect ALL classes first for debugging, then filter
        results = model(
            frame,
            conf=confidence_threshold,
            iou=0.5,
            imgsz=img_size,
            verbose=False,
        )

        detections = []
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                # Debug: log class distribution for first few frames
                all_cls = [int(c) for c in boxes.cls.cpu().numpy()]
                from collections import Counter
                cls_counts = Counter(all_cls)
                # Get model class names
                model_names = result.names if hasattr(result, 'names') else {}
                top5 = cls_counts.most_common(5)
                top5_str = ', '.join(f'{model_names.get(c, c)}({n})' for c, n in top5)
                if not hasattr(detect_objects, '_debug_logged'):
                    detect_objects._debug_logged = 0
                if detect_objects._debug_logged < 3:
                    detect_objects._debug_logged += 1
                    logger.info(f"[detect] Raw YOLO output: {len(boxes)} boxes, top classes: {top5_str}")

                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i])
                    conf = float(boxes.conf[i])
                    xyxy = boxes.xyxy[i].cpu().numpy()

                    # Filter to person and ball only
                    obj_type = COCO_CLASSES.get(cls_id)
                    if obj_type is None:
                        continue

                    x1, y1, x2, y2 = xyxy.tolist()
                    detections.append({
                        "type": obj_type,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": conf,
                    })

        # Extract pose keypoints using separate pose model (if enabled)
        if POSE_ENABLED and detections:
            pose_model = _get_pose_model()
            if pose_model is not None:
                _extract_pose_keypoints(frame, detections, pose_model, img_size)
            else:
                # Fall back to MediaPipe if if available
                _extract_mediapipe_keypoints(frame, detections)

        # Debug: log filtered summary for first few frames
        if not hasattr(detect_objects, '_debug_summary'):
            detect_objects._debug_summary = 0
        if detect_objects._debug_summary < 3:
            detect_objects._debug_summary += 1
            p_count = sum(1 for d in detections if d['type'] == 'player')
            b_count = sum(1 for d in detections if d['type'] == 'ball')
            logger.info(f"[detect] Frame filtered: {p_count} players, {b_count} balls, total={len(detections)}")

        return detections

    except Exception as e:
        logger.error(f"[detect] Detection failed: {e}")
        return []


def _extract_pose_keypoints(
    frame: np.ndarray,
    detections: List[Dict],
    pose_model,
    img_size: int = 640,
):
    """Extract keypoints using YOLO11-pose model on cropped player regions."""
    for det in detections:
        if det["type"] != "player":
            continue

        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        h_frame, w_frame = frame.shape[:2]

        # Clamp to frame
        x1 = max(0, min(x1, w_frame - 1))
        y1 = max(0, min(y1, h_frame - 1))
        x2 = max(x1 + 1, min(x2, w_frame))
        y2 = max(y1 + 1, min(y2, h_frame))

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        try:
            results = pose_model(crop, conf=0.3, imgsz=img_size, verbose=False)
            if results and len(results) > 0 and results[0].keypoints is not None:
                kps = results[0].keypoints
                if kps is not None and len(kps) > 0:
                    # Get first person's keypoints
                    kp_xy = kps.xy[0].cpu().numpy()  # (17, 2) or (N, 2)
                    kp_conf = kps.conf[0].cpu().numpy() if kps.conf is not None else np.ones(len(kp_xy))

                    crop_h, crop_w = crop.shape[:2]
                    keypoints = []
                    for j in range(len(kp_xy)):
                        kp = {
                            "x": float(kp_xy[j][0]) / crop_w if crop_w > 0 else 0,
                            "y": float(kp_xy[j][1]) / crop_h if crop_h > 0 else 0,
                            "z": 0.0,
                            "visibility": float(kp_conf[j]) if j < len(kp_conf) else 0.0,
                        }
                        keypoints.append(kp)

                    det["keypoints"] = keypoints
        except Exception as e:
            logger.debug(f"[pose] Keypoint extraction failed for crop: {e}")


def _extract_mediapipe_keypoints(frame: np.ndarray, detections: List[Dict]):
    """Fallback: extract keypoints using MediaPipe on cropped player regions."""
    try:
        from pose_estimation import extract_pose_keypoints
        for det in detections:
            if det["type"] != "player":
                continue
            try:
                keypoints = extract_pose_keypoints(frame, tuple(det["bbox"]))
                if keypoints:
                    det["keypoints"] = keypoints
            except Exception:
                pass
    except ImportError:
        pass


def read_jersey_number(frame: np.ndarray, bbox: list) -> str:
    """Read jersey number from the upper portion of a player bounding box."""
    try:
        import pytesseract
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
    except Exception:
        return ""


def reset_detection():
    """Reset all detection state (call between videos)."""
    global _detect_model, _pose_model
    # Don't clear the models — they're heavy to reload
    # Just reset any per-video state if needed
    try:
        from pose_estimation import reset_pose
        reset_pose()
    except Exception:
        pass
