import pytest
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from smoothing import smooth_trajectory

def test_smooth_trajectory_reduces_jitter():
    noisy = [(float(i), 0.0, float(i) + (1.0 if i % 2 == 0 else -1.0)) for i in range(20)]
    smoothed = smooth_trajectory(noisy)
    assert len(smoothed) == len(noisy)
    max_noise = max(abs(noisy[i][2] - i) for i in range(len(noisy)))
    max_smoothed = max(abs(smoothed[i][2] - i) for i in range(len(noisy)))
    assert max_smoothed < max_noise

def test_smooth_trajectory_short():
    assert smooth_trajectory([(0.0, 0.0, 0.0)]) == [(0.0, 0.0, 0.0)]

def test_smooth_trajectory_empty():
    assert smooth_trajectory([]) == []
