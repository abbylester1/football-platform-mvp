import pytest
from backend.tracking import track_objects, reset_tracker

@pytest.fixture(autouse=True)
def reset_tracking():
    reset_tracker()

def test_track_objects_assigns_ids():
    detections = [
        {"type": "player", "bbox": [10, 10, 50, 80], "confidence": 0.9},
        {"type": "player", "bbox": [100, 100, 140, 180], "confidence": 0.85},
        {"type": "ball", "bbox": [200, 150, 210, 160], "confidence": 0.7},
    ]
    tracked = track_objects(detections, frame_idx=0)
    assert len(tracked) == 3
    for obj in tracked:
        assert "track_id" in obj
        assert isinstance(obj["track_id"], int)

def test_track_objects_stable_ids_across_frames():
    d1 = [{"type": "player", "bbox": [10, 10, 50, 80], "confidence": 0.9}]
    d2 = [{"type": "player", "bbox": [12, 12, 52, 82], "confidence": 0.9}]
    t1 = track_objects(d1, frame_idx=0)
    t2 = track_objects(d2, frame_idx=1)
    assert t1[0]["track_id"] == t2[0]["track_id"]

def test_track_objects_empty():
    assert track_objects([], frame_idx=0) == []
