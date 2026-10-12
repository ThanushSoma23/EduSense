import cv2
import numpy as np
from typing import Tuple

def deskew_image(img: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Deskew image: estimate skew angle from text lines (minAreaRect or projection profile),
    correct within +/-15 deg. Returns (rotated_img, angle_applied).
    """
    if img is None or img.size == 0:
        return img, 0.0

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return img, 0.0

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Clamp to +/-15 deg
    if abs(angle) > 15.0:
        angle = 0.0

    if abs(angle) < 0.2:
        return img, 0.0

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated, float(round(angle, 2))
