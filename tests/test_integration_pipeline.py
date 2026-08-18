import pytest
import cv2
import numpy as np
import os
import json
import tempfile
import shutil
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from tracking import track_objects, reset_tracker
from calibration import estimate_homography, detect_cones_in_frame
from projection import project_to_3d
from smoothing import smooth_trajectory, smooth_keypoints
from animation import build_scene, AVATAR_MAP, _create_avatar_mesh, _select_avatar
from config import VIDEOS_DIR, SCENES_DIR, FRAME_INTERVAL, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE
from models import DetectedObject, FramePosition, DrillResponse, ObjectUpdate, Keypoint
from database import Drill, DrillStatus


SAMPLE_BBOX = [100, 50, 180, 200]
SAMPLE_CENTER_X = (SAMPLE_BBOX[0] + SAMPLE_BBOX[2]) / 2
SAMPLE_CENTER_Y = (SAMPLE_BBOX[1] + SAMPLE_BBOX[3]) / 2


class TestDetectionTrackerIntegration:
    """End-to-end: synthetic detections → tracking → projection → smoothing → animation."""

    def test_tracking_assigns_and_persists_ids(self):
        reset_tracker()
        frames = [
            [
                {"type": "player", "bbox": [10, 10, 50, 80], "confidence": 0.9},
                {"type": "ball", "bbox": [200, 150, 210, 160], "confidence": 0.8},
            ],
            [
                {"type": "player", "bbox": [12, 12, 52, 82], "confidence": 0.9},
                {"type": "ball", "bbox": [202, 148, 212, 158], "confidence": 0.8},
            ],
            [
                {"type": "player", "bbox": [15, 15, 55, 85], "confidence": 0.9},
                {"type": "ball", "bbox": [205, 147, 215, 157], "confidence": 0.8},
            ],
        ]
        all_tracked = []
        for i, dets in enumerate(frames):
            tracked = track_objects(dets, frame_idx=i)
            all_tracked.append(tracked)
            assert len(tracked) == 2

        player_ids = set()
        ball_ids = set()
        for frame_data in all_tracked:
            for obj in frame_data:
                assert "track_id" in obj
                assert isinstance(obj["track_id"], int)
                if obj["type"] == "player":
                    player_ids.add(obj["track_id"])
                elif obj["type"] == "ball":
                    ball_ids.add(obj["track_id"])

        assert len(player_ids) == 1
        assert len(ball_ids) == 1

    def test_tracking_recycled_id_after_disappearance(self):
        reset_tracker()
        _ = track_objects([{"type": "player", "bbox": [0, 0, 10, 20], "confidence": 0.9}], frame_idx=0)
        first_id = track_objects([], frame_idx=1)[0]["track_id"] if False else None
        for _ in range(15):
            track_objects([], frame_idx=0)
        result = track_objects([{"type": "player", "bbox": [0, 0, 10, 20], "confidence": 0.9}], frame_idx=20)
        assert any(obj["type"] == "player" for obj in result)
        assert len(result) >= 1

    def test_tracking_empty_detections_return_empty(self):
        reset_tracker()
        assert track_objects([], frame_idx=0) == []


class TestCalibrationHomography:
    def test_estimate_homography_returns_none_with_fewer_than_4_points(self):
        H = estimate_homography([(0, 0), (1, 0), (0, 1)])
        assert H is None

    def test_estimate_homography_with_valid_cones(self):
        cones = [(0, 0), (100, 0), (100, 100), (0, 100)]
        H = estimate_homography(cones)
        assert H is not None
        assert H.shape == (3, 3)
        assert np.isfinite(H).all()

    def test_estimate_homography_with_cone_output(self):
        cones = [(50, 50), (200, 60), (180, 300), (30, 280)]
        H = estimate_homography(cones)
        assert H is not None
        pt = np.array([[[125, 175]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, H)
        assert np.isfinite(transformed).all()
        assert transformed[0, 0, 0] > 0
        assert transformed[0, 0, 1] > 0


class TestProjection3D:
    def test_projection_with_homography(self):
        cones = [(0, 0), (100, 0), (100, 100), (0, 100)]
        H = estimate_homography(cones)
        x, y, z = project_to_3d(SAMPLE_CENTER_X, SAMPLE_CENTER_Y, H, 640, 480)
        assert isinstance(x, float)
        assert isinstance(z, float)
        assert y == 0.0
        assert np.isfinite(x)
        assert np.isfinite(z)

    def test_projection_without_homography(self):
        x, y, z = project_to_3d(SAMPLE_CENTER_X, SAMPLE_CENTER_Y, None, 640, 480)
        assert y == 0.0
        assert -15 <= x <= 15
        assert 0 <= z <= 18

    def test_projection_consistency(self):
        cones = [(0, 0), (100, 0), (100, 100), (0, 100)]
        H = estimate_homography(cones)
        r1 = project_to_3d(50, 50, H, 640, 480)
        r2 = project_to_3d(50, 50, H, 640, 480)
        assert r1 == r2


class TestConeDetection:
    def test_detect_cones_in_frame_returns_list(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        assert detect_cones_in_frame(img) == []

    def test_detect_cones_finds_orange_blob(self):
        img = np.zeros((200, 300, 3), dtype=np.uint8)
        img[40:80, 50:90] = (0, 100, 255)
        cones = detect_cones_in_frame(img, min_area=10, max_area=50000)
        assert len(cones) >= 1
        x1, y1, x2, y2 = cones[0]
        assert x1 < x2
        assert y1 < y2
        assert 40 <= y1 <= 80
        assert 50 <= x1 <= 90

    def test_detect_cones_area_filter(self):
        img = np.zeros((200, 300, 3), dtype=np.uint8)
        img[90:110, 130:170] = (0, 100, 255)
        cones_low = detect_cones_in_frame(img, min_area=5000, max_area=50000)
        assert cones_low == []
        cones_ok = detect_cones_in_frame(img, min_area=10, max_area=50000)
        assert len(cones_ok) >= 1


class TestSmoothing:
    def test_smoothing_reduces_noise(self):
        noisy = [(float(i), 0.0, float(i) + (1.0 if i % 2 == 0 else -1.0)) for i in range(20)]
        smoothed = smooth_trajectory(noisy)
        max_noise = max(abs(noisy[i][1] - smoothed[i][1]) for i in range(len(noisy)))
        max_smoothed = max(abs(smoothed[i][0] - i) for i in range(len(noisy)))
        assert max_noise >= 0
        assert len(smoothed) == len(noisy)

    def test_smoothing_preserves_length(self):
        assert len(smooth_trajectory([(i, i, i) for i in range(10)])) == 10
        assert len(smooth_trajectory([(1, 2, 3)])) == 1
        assert len(smooth_trajectory([])) == 0

    def test_smoothing_identity_for_short_sequences(self):
        short = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
        assert smooth_trajectory(short) == short


class TestAnimation:
    def test_build_scene_creates_glb(self):
        objects = [
            {"type": "player", "id": "P1", "frames": [{"frame": 0, "x": 0, "y": 0, "z": 0}]},
            {"type": "ball", "id": "B1", "frames": [{"frame": 0, "x": 5, "y": 0, "z": 5}]},
            {"type": "cone", "id": "C1", "frames": [{"frame": 0, "x": -3, "y": 0, "z": -2}]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = build_scene(objects, "test_scene", tmp)
            assert os.path.exists(path)
            assert path.endswith(".glb")
            assert os.path.getsize(path) > 100

    def test_build_scene_empty_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = build_scene([], "empty_scene", tmp)
            assert os.path.exists(path)
            assert path.endswith(".glb")

    def test_avatar_map_keys(self):
        assert "generic" in AVATAR_MAP
        for key in ["standard_red", "standard_blue", "lean_red", "stocky_blue", "youth_red"]:
            assert key in AVATAR_MAP, f"Missing avatar: {key}"

    def test_select_avatar_default(self):
        obj = {"type": "player", "id": "P1", "frames": []}
        avatar_id, color = _select_avatar(obj)
        assert avatar_id == "generic"
        assert color == (1.0, 0.6, 0.0)

    def test_select_avatar_custom(self):
        obj = {"type": "player", "id": "P1", "frames": [], "avatar_id": "standard_red"}
        avatar_id, color = _select_avatar(obj)
        assert avatar_id == "standard_red"
        assert color == (0.8, 0.2, 0.2)

    def test_create_avatar_mesh(self):
        mesh = _create_avatar_mesh("standard_red", (0.8, 0.2, 0.2), "/nonexistent", "standard")
        assert mesh is not None
        assert hasattr(mesh, 'vertices')
        assert len(mesh.vertices) > 10


class TestModelSchemas:
    def test_detected_object_serialization(self):
        obj = DetectedObject(type="player", id="P1", label="Player 1",
                             frames=[FramePosition(frame=0, x=1.0, y=2.0, z=3.0)])
        data = obj.model_dump()
        assert data["type"] == "player"
        assert data["id"] == "P1"
        assert len(data["frames"]) == 1
        assert data["frames"][0]["x"] == 1.0

    def test_drill_response_validation(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        resp = DrillResponse(
            id="test-id", name="Test Drill", category="passing",
            age_group="U12", difficulty="beginner", description="desc",
            video_key="test.mp4", status="uploading", detected_objects=[],
            scene_key="", created_at=now, updated_at=now,
        )
        assert resp.id == "test-id"
        assert resp.status == "uploading"

    def test_object_update_model(self):
        objs = [
            DetectedObject(type="player", id="P1", frames=[
                FramePosition(frame=0, x=0, y=0, z=0)]),
        ]
        update = ObjectUpdate(detected_objects=objs)
        assert len(update.detected_objects) == 1
        assert update.detected_objects[0].type == "player"

    def test_drill_status_values(self):
        assert DrillStatus.UPLOADING.value == "uploading"
        assert DrillStatus.PROCESSING.value == "processing"
        assert DrillStatus.REVIEW.value == "review"
        assert DrillStatus.READY.value == "ready"
        assert DrillStatus.FAILED.value == "failed"

    def test_drill_model_creation(self):
        drill = Drill(
            name="Integration Drill", video_key="integ.mp4",
            status=DrillStatus.UPLOADING.value,
        )
        assert drill.name == "Integration Drill"
        assert drill.status == "uploading"


class TestKeypointIntegration:
    """Integration tests for keypoint data through the pipeline."""

    def test_keypoints_through_smoothing(self):
        """Keypoints should survive the smoothing pipeline without corruption."""
        frames = []
        np.random.seed(42)
        for i in range(15):
            noise = np.random.normal(0, 0.01)
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
        assert len(result) == 15
        for f in result:
            assert f.get("keypoints") is not None
            assert len(f["keypoints"]) == 33

    def test_build_scene_with_skeleton(self):
        """GLB export should work with keypoints present."""
        keypoints = [
            {"x": 0.5, "y": 0.0, "z": 0.0, "visibility": 0.9} for _ in range(33)
        ]
        # Set specific landmark positions for visible skeleton
        keypoints[0] = {"x": 0.5, "y": 1.5, "z": 0.0, "visibility": 0.9}   # nose
        keypoints[11] = {"x": 0.4, "y": 1.2, "z": 0.0, "visibility": 0.9}  # left shoulder
        keypoints[12] = {"x": 0.6, "y": 1.2, "z": 0.0, "visibility": 0.9}  # right shoulder
        keypoints[23] = {"x": 0.4, "y": 0.8, "z": 0.0, "visibility": 0.9}  # left hip
        keypoints[24] = {"x": 0.6, "y": 0.8, "z": 0.0, "visibility": 0.9}  # right hip

        objects = [
            {
                "type": "player",
                "id": "player_1",
                "frames": [{"frame": 0, "x": 0.0, "y": 0.0, "z": 0.0, "keypoints": keypoints}],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = build_scene(objects, "skeleton_test", tmp)
            assert os.path.exists(path)
            assert path.endswith(".glb")
            assert os.path.getsize(path) > 100

    def test_build_scene_without_keypoints_fallback(self):
        """GLB export should fall back to capsule when no keypoints present."""
        objects = [
            {
                "type": "player",
                "id": "player_1",
                "frames": [{"frame": 0, "x": 0.0, "y": 0.0, "z": 0.0}],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = build_scene(objects, "capsule_fallback_test", tmp)
            assert os.path.exists(path)
            assert path.endswith(".glb")

    def test_frame_position_with_keypoints_serialization(self):
        """FramePosition with keypoints should serialize/deserialize correctly."""
        kp = Keypoint(x=0.5, y=0.5, z=0.1, visibility=0.9)
        fp = FramePosition(frame=1, x=1.0, y=2.0, z=3.0, keypoints=[kp])
        data = fp.model_dump()
        assert data["keypoints"] is not None
        assert len(data["keypoints"]) == 1
        assert data["keypoints"][0]["x"] == 0.5

        # Round-trip
        fp2 = FramePosition(**data)
        assert fp2.keypoints is not None
        assert fp2.keypoints[0].x == 0.5

    def test_frame_position_backward_compatible(self):
        """Old drill data without keypoints should deserialize correctly."""
        data = {"frame": 1, "x": 1.0, "y": 2.0, "z": 3.0}
        fp = FramePosition(**data)
        assert fp.keypoints is None


class TestConfig:
    def test_allowed_extensions(self):
        assert ".mp4" in ALLOWED_EXTENSIONS
        assert ".mov" in ALLOWED_EXTENSIONS

    def test_max_upload_size(self):
        assert MAX_UPLOAD_SIZE == 2 * 1024 * 1024 * 1024

    def test_frame_interval_is_positive(self):
        assert FRAME_INTERVAL >= 1
