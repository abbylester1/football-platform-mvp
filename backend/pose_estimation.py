"""MediaPipe Pose estimation wrapper for football player skeletal analysis.

Extracts 33 body landmarks from cropped player regions detected by YOLO.
Keypoints are normalized to 0-1 relative to the crop bounding box for
resolution independence.

MediaPipe Pose landmarks (33 total):
  0: nose, 1-10: face, 11: left_shoulder, 12: right_shoulder,
  13: left_elbow, 14: right_elbow, 15: left_wrist, 16: right_wrist,
  17-22: hands, 23: left_hip, 24: right_hip, 25: left_knee,
  26: right_knee, 27: left_ankle, 28: right_ankle, 29-32: feet
"""

import logging
import cv2
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import to handle environments where mediapipe isn't available
_mp = None
_mp_pose = None
_pose_instance = None
_mediapipe_available = None  # None = not checked yet


def _check_mediapipe():
    """Check if mediapipe is available and import it lazily."""
    global _mp, _mp_pose, _mediapipe_available
    if _mediapipe_available is not None:
        return _mediapipe_available
    try:
        import mediapipe as mp
        _mp = mp
        _mp_pose = mp.solutions.pose
        _mediapipe_available = True
        logger.info("MediaPipe Pose loaded successfully")
    except ImportError as e:
        logger.warning(f"MediaPipe not available: {e}. Pose estimation disabled.")
        _mediapipe_available = False
    except Exception as e:
        logger.warning(f"MediaPipe failed to initialize: {e}. Pose estimation disabled.")
        _mediapipe_available = False
    return _mediapipe_available


def _get_pose():
    """Get or initialize MediaPipe Pose instance (singleton)."""
    global _pose_instance
    if not _check_mediapipe():
        return None
    if _pose_instance is None:
        try:
            _pose_instance = _mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,  # 0=lite, 1=full, 2=heavy
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize MediaPipe Pose: {e}")
            return None
    return _pose_instance


def reset_pose():
    """Reset the MediaPipe Pose instance (call between videos)."""
    global _pose_instance
    if _pose_instance is not None:
        try:
            _pose_instance.close()
        except Exception:
            pass
        _pose_instance = None


def extract_pose_keypoints(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],
    confidence_threshold: float = 0.5,
) -> Optional[list[dict]]:
    """Run MediaPipe Pose on a cropped player region.

    Args:
        frame: Full BGR frame from video (H, W, 3).
        bbox: Bounding box (x1, y1, x2, y2) in pixel coordinates.
        confidence_threshold: Minimum visibility for a landmark to be included.

    Returns:
        List of 33 landmark dicts with keys {x, y, z, visibility},
        or None if pose detection fails entirely.
        Coordinates are normalized 0-1 relative to the crop bbox.
    """
    # Gracefully return None if mediapipe is not available
    if not _check_mediapipe():
        return None

    try:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h_frame, w_frame = frame.shape[:2]

        # Clamp to frame bounds
        x1 = max(0, min(x1, w_frame - 1))
        y1 = max(0, min(y1, h_frame - 1))
        x2 = max(x1 + 1, min(x2, w_frame))
        y2 = max(y1 + 1, min(y2, h_frame))

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        # MediaPipe expects RGB
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        pose = _get_pose()
        if pose is None:
            return None

        results = pose.process(crop_rgb)

        if not results.pose_landmarks:
            return None

        landmarks = results.pose_landmarks.landmark
        keypoints = []

        for lm in landmarks:
            kp = {
                "x": lm.x,  # Already normalized 0-1 relative to crop
                "y": lm.y,  # Already normalized 0-1 relative to crop
                "z": lm.z,  # Relative depth
                "visibility": lm.visibility,
            }
            keypoints.append(kp)

        return keypoints
    except Exception as e:
        logger.warning(f"Pose extraction failed: {e}")
        return None


def get_skeleton_connections() -> list[tuple[int, int]]:
    """Return the 12 bone connections for the stick figure renderer.

    Uses COCO-format MediaPipe landmark indices for the body skeleton.
    """
    return [
        (11, 12),  # shoulders
        (11, 13),  # left upper arm
        (13, 15),  # left forearm
        (12, 14),  # right upper arm
        (14, 16),  # right forearm
        (11, 23),  # left torso
        (12, 24),  # right torso
        (23, 24),  # hips
        (23, 25),  # left upper leg
        (25, 27),  # left lower leg
        (24, 26),  # right upper leg
        (26, 28),  # right lower leg
    ]


def get_joint_indices() -> list[int]:
    """Return the landmark indices used as visible joints in the stick figure."""
    return [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
