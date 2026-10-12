import cv2
import numpy as np
from typing import Tuple

def enhance_contrast_clahe(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply CLAHE to produce BOTH:
    1. Grayscale-enhanced image (for TrOCR)
    2. Binarised image (for EasyOCR / line detection)
    Never binarises destructively; returns (enhanced_gray, binarised).
    """
    if img is None or img.size == 0:
        return img, img

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)

    # Adaptive Otsu binarization
    binarised = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    return enhanced_gray, binarised
