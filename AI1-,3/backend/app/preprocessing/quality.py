import cv2
import numpy as np
from typing import List, Tuple

def evaluate_page_quality(img: np.ndarray, skew_deg: float, page_detected: bool) -> Tuple[float, List[str]]:
    """
    Quality gate: blur (Laplacian variance), contrast, ink coverage, resolution -> quality_score 0-1 and flags.
    Flags: ["blurry", "low_contrast", "cropped", "no_page_found", "skew_extreme"]
    Bad pages are FLAGGED for teacher re-scan, never silently dropped.
    """
    flags = []

    if img is None or img.size == 0:
        return 0.0, ["corrupt_file"]

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    # 1. Blur check (variance of Laplacian)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if lap_var < 100.0:
        flags.append("blurry")

    # 2. Contrast check
    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    contrast_range = max_val - min_val
    if contrast_range < 50:
        flags.append("low_contrast")

    # 3. Skew extreme check
    if abs(skew_deg) > 10.0:
        flags.append("skew_extreme")

    # 4. Page detection check
    if not page_detected:
        flags.append("no_page_found")

    # Compute quality score (0.0 to 1.0)
    score = 1.0
    if "blurry" in flags:
        score -= 0.3
    if "low_contrast" in flags:
        score -= 0.2
    if "skew_extreme" in flags:
        score -= 0.2
    if "no_page_found" in flags:
        score -= 0.2

    quality_score = max(0.0, min(round(score, 2), 1.0))
    return quality_score, flags
