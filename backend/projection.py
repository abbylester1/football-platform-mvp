import numpy as np
import cv2

def project_to_3d(
    x: float,
    y: float,
    homography,
    frame_width: int = 640,
    frame_height: int = 480,
    field_scale: float = 30.0,
):
    if homography is not None:
        pt = np.array([[[x, y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, homography)
        return (float(transformed[0, 0, 0]), 0.0, float(transformed[0, 0, 1]))

    nx = (x / frame_width) * field_scale - field_scale / 2
    nz = (1.0 - y / frame_height) * field_scale * 0.6
    return (nx, 0.0, nz)
