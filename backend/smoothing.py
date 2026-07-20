import numpy as np
from scipy.signal import savgol_filter

def smooth_trajectory(positions: list[tuple[float, float, float]], window: int = 5, polyorder: int = 2) -> list[tuple[float, float, float]]:
    if len(positions) <= window:
        return positions

    arr = np.array(positions)
    smoothed = np.copy(arr)

    for dim in range(3):
        col = arr[:, dim]
        w = min(window, len(col) if len(col) % 2 == 1 else len(col) - 1)
        if w < 3:
            continue
        try:
            smoothed[:, dim] = savgol_filter(col, w, polyorder)
        except Exception:
            pass

    return [(float(x), float(y), float(z)) for x, y, z in smoothed]
