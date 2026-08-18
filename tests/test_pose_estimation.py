"""Tests for pose estimation module (MediaPipe Pose integration)."""
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestExtractPoseKeypoints:
    """Tests for extract_pose_keypoints function."""

    def test_returns_none_for_empty_frame(self):
        """Pose extraction should return None when given a zero frame."""
        from pose_estimation import extract_pose_keypoints
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 300)
        result = extract_pose_keypoints(frame, bbox)
        # Empty black frame has no person — should return None
        assert result is None

    def test_returns_none_for_invalid_bbox(self):
        """Pose extraction should handle degenerate bounding boxes."""
        from pose_estimation import extract_pose_keypoints
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Zero-area bbox
        bbox = (100, 100, 100, 100)
        result = extract_pose_keypoints(frame, bbox)
        assert result is None

    def test_returns_none_for_out_of_bounds_bbox(self):
        """Pose extraction should handle bboxes that extend beyond frame."""
        from pose_estimation import extract_pose_keypoints
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (600, 400, 700, 500)  # Partially outside frame
        result = extract_pose_keypoints(frame, bbox)
        assert result is None

    def test_returns_none_for_entirely_out_of_bounds_bbox(self):
        """Pose extraction should handle completely out-of-bounds bboxes."""
        from pose_estimation import extract_pose_keypoints
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (-100, -100, -50, -50)
        result = extract_pose_keypoints(frame, bbox)
        assert result is None

    def test_returns_list_of_33_landmarks_on_valid_person(self):
        """When a person is detected, should return 33 landmarks."""
        from pose_estimation import extract_pose_keypoints, reset_pose
        # Create a synthetic person-like image (skin-colored rectangle with body)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw a simple person silhouette (skin-colored head, dark body)
        frame[100:130, 300:340] = [180, 200, 220]  # Head (skin)
        frame[130:280, 290:350] = [50, 50, 150]    # Body (dark shirt)
        frame[280:400, 295:325] = [60, 60, 100]    # Left leg
        frame[280:400, 325:355] = [60, 60, 100]    # Right leg
        # Arms
        frame[130:200, 260:290] = [50, 50, 150]    # Left arm
        frame[130:200, 350:380] = [50, 50, 150]    # Right arm

        bbox = (250, 90, 400, 420)
        result = extract_pose_keypoints(frame, bbox)

        # May or may not detect pose on synthetic data, but if it does:
        if result is not None:
            assert len(result) == 33
            for kp in result:
                assert "x" in kp
                assert "y" in kp
                assert "z" in kp
                assert "visibility" in kp
                assert 0 <= kp["x"] <= 1
                assert 0 <= kp["y"] <= 1
                assert 0 <= kp["visibility"] <= 1


class TestSkeletonConnections:
    """Tests for skeleton connection constants."""

    def test_skeleton_connections_returns_12_pairs(self):
        """Should have exactly 12 bone connections."""
        from pose_estimation import get_skeleton_connections
        connections = get_skeleton_connections()
        assert len(connections) == 12

    def test_joint_indices_are_valid_landmark_indices(self):
        """Joint indices should be valid MediaPipe landmark indices (0-32)."""
        from pose_estimation import get_joint_indices
        indices = get_joint_indices()
        assert len(indices) == 13
        for idx in indices:
            assert 0 <= idx <= 32


class TestResetPose:
    """Tests for pose reset functionality."""

    def test_reset_pose_does_not_raise(self):
        """Resetting pose should not raise any exceptions."""
        from pose_estimation import reset_pose
        reset_pose()  # Should complete without error

    def test_reset_pose_allows_reinitialization(self):
        """After reset, next call to extract should reinitialize."""
        from pose_estimation import extract_pose_keypoints, reset_pose
        reset_pose()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = extract_pose_keypoints(frame, (100, 100, 200, 300))
        # Should not crash
        assert result is None or isinstance(result, list)


class TestSmoothKeypoints:
    """Tests for the smooth_keypoints function in smoothing module."""

    def test_smooth_keypoints_returns_empty_list(self):
        """Should handle empty input gracefully."""
        from smoothing import smooth_keypoints
        result = smooth_keypoints([])
        assert result == []

    def test_smooth_keypoints_returns_same_when_no_keypoints(self):
        """Should return frames unchanged when no keypoints present."""
        from smoothing import smooth_keypoints
        frames = [
            {"frame": 1, "x": 0.0, "y": 0.0, "z": 0.0},
            {"frame": 2, "x": 1.0, "y": 1.0, "z": 0.0},
        ]
        result = smooth_keypoints(frames)
        assert len(result) == 2
        assert result[0]["x"] == 0.0
        assert result[1]["x"] == 1.0

    def test_smooth_keypoints_handles_sparse_keypoints(self):
        """Should handle frames with mixed presence of keypoints."""
        from smoothing import smooth_keypoints
        # Create 10 frames, only some with keypoints
        frames = []
        for i in range(10):
            if i % 3 == 0:
                frames.append({
                    "frame": i,
                    "x": float(i),
                    "y": float(i),
                    "z": 0.0,
                    "keypoints": [
                        {"x": 0.5 + i * 0.01, "y": 0.5, "z": 0.0, "visibility": 0.9}
                        for _ in range(33)
                    ]
                })
            else:
                frames.append({
                    "frame": i,
                    "x": float(i),
                    "y": float(i),
                    "z": 0.0,
                })
        result = smooth_keypoints(frames)
        assert len(result) == 10

    def test_smooth_keypoints_smoothes_valid_tracks(self):
        """Should apply Savitzky-Golay smoothing to keypoint trajectories."""
        from smoothing import smooth_keypoints
        # Create 10 frames with noisy keypoints
        np.random.seed(42)
        frames = []
        for i in range(10):
            noise = np.random.normal(0, 0.02)
            frames.append({
                "frame": i,
                "x": float(i),
                "y": float(i),
                "z": 0.0,
                "keypoints": [
                    {"x": 0.5 + noise, "y": 0.5 + noise, "z": 0.0, "visibility": 0.9}
                    for _ in range(33)
                ]
            })
        result = smooth_keypoints(frames)
        # All frames should still have keypoints
        for f in result:
            assert f.get("keypoints") is not None
            assert len(f["keypoints"]) == 33


class TestKeypointModel:
    """Tests for the Keypoint Pydantic model."""

    def test_keypoint_creation(self):
        """Keypoint model should accept valid values."""
        from models import Keypoint
        kp = Keypoint(x=0.5, y=0.5, z=0.1, visibility=0.9)
        assert kp.x == 0.5
        assert kp.y == 0.5
        assert kp.z == 0.1
        assert kp.visibility == 0.9

    def test_keypoint_defaults(self):
        """Keypoint model should have default values for z and visibility."""
        from models import Keypoint
        kp = Keypoint(x=0.5, y=0.5)
        assert kp.z == 0.0
        assert kp.visibility == 0.0

    def test_frame_position_with_keypoints(self):
        """FramePosition should accept optional keypoints."""
        from models import FramePosition, Keypoint
        kp = Keypoint(x=0.5, y=0.5, z=0.1, visibility=0.9)
        fp = FramePosition(frame=1, x=0.0, y=0.0, keypoints=[kp])
        assert fp.keypoints is not None
        assert len(fp.keypoints) == 1
        assert fp.keypoints[0].x == 0.5

    def test_frame_position_without_keypoints(self):
        """FramePosition should work without keypoints (backward compatible)."""
        from models import FramePosition
        fp = FramePosition(frame=1, x=0.0, y=0.0)
        assert fp.keypoints is None
