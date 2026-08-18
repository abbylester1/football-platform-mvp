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


def smooth_keypoints(
    frames: list[dict],
    window: int = 5,
    polyorder: int = 2,
    visibility_threshold: float = 0.5,
) -> list[dict]:
    """Apply Savitzky-Golay filtering to keypoint trajectories per frame list.

    Each of the 33 landmarks gets smoothed independently across frames.
    Only landmarks with visibility above the threshold are smoothed.

    Args:
        frames: List of frame dicts with optional 'keypoints' field.
        window: Savitzky-Golay window size (must be odd, >= polyorder + 1).
        polyorder: Polynomial order for the filter.
        visibility_threshold: Minimum visibility to include a landmark.

    Returns:
        Same frames list with keypoints smoothed in-place.
    """
    if not frames:
        return frames

    # Collect frames that have keypoints
    kp_frames = [(i, f) for i, f in enumerate(frames) if f.get("keypoints")]
    if len(kp_frames) < window:
        return frames

    num_landmarks = len(kp_frames[0][1]["keypoints"])

    for landmark_idx in range(num_landmarks):
        x_values = []
        y_values = []
        valid_indices = []

        for frame_idx, frame in kp_frames:
            kps = frame["keypoints"]
            if landmark_idx < len(kps) and kps[landmark_idx]["visibility"] > visibility_threshold:
                x_values.append(kps[landmark_idx]["x"])
                y_values.append(kps[landmark_idx]["y"])
                valid_indices.append(frame_idx)

        if len(x_values) < window:
            continue

        x_arr = np.array(x_values)
        y_arr = np.array(y_values)

        w = min(window, len(x_arr) if len(x_arr) % 2 == 1 else len(x_arr) - 1)
        if w < 3:
            continue

        try:
            smoothed_x = savgol_filter(x_arr, w, polyorder)
            smoothed_y = savgol_filter(y_arr, w, polyorder)
            for i, frame_idx in enumerate(valid_indices):
                frames[frame_idx]["keypoints"][landmark_idx]["x"] = float(smoothed_x[i])
                frames[frame_idx]["keypoints"][landmark_idx]["y"] = float(smoothed_y[i])
        except Exception:
            pass

    return frames
