import pytest
import os
import tempfile
from backend.animation import build_scene

def test_build_scene_returns_glb_path():
    objects = [
        {"type": "player", "id": "P1", "frames": [{"frame": 0, "x": 0, "y": 0, "z": 0}, {"frame": 1, "x": 1, "y": 0, "z": 1}]},
        {"type": "ball", "id": "B1", "frames": [{"frame": 0, "x": 2, "y": 0, "z": 2}]},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = build_scene(objects, "test_drill", tmp)
        assert path.endswith(".glb")
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

def test_build_scene_with_empty_objects():
    with tempfile.TemporaryDirectory() as tmp:
        path = build_scene([], "empty_drill", tmp)
        assert path.endswith(".glb")
        assert os.path.exists(path)
