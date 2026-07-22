import pytest
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from detection import detect_objects

def test_detect_objects_returns_list():
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detect_objects(dummy_frame)
    assert isinstance(results, list)
    if results:
        for obj in results:
            assert "type" in obj
            assert "bbox" in obj
            assert "confidence" in obj
            assert obj["type"] in ("player", "ball", "cone")
            assert len(obj["bbox"]) == 4

def test_detect_objects_handles_empty_frame():
    results = detect_objects(None)
    assert results == []

def test_detect_objects_confidence_threshold():
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detect_objects(dummy_frame, confidence_threshold=0.99)
    assert isinstance(results, list)
