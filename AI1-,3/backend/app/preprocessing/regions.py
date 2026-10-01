import cv2
import numpy as np
from typing import List, Dict, Any

def extract_line_regions(binarised_img: np.ndarray, page_number: int = 1) -> List[Dict[str, Any]]:
    """
    Split page into line crops via horizontal projection profile + connected components.
    Returns bboxes in page coordinates: [{"bbox": [x, y, w, h], "page_number": page_number}].
    """
    if binarised_img is None or binarised_img.size == 0:
        return []

    # Invert image (text = white)
    inv = 255 - binarised_img if binarised_img.max() == 255 else binarised_img

    # Horizontal projection profile
    proj = np.sum(inv, axis=1)
    thresh_val = np.max(proj) * 0.05 if np.max(proj) > 0 else 0

    in_line = False
    start_y = 0
    lines = []

    for y, val in enumerate(proj):
        if val > thresh_val and not in_line:
            in_line = True
            start_y = y
        elif val <= thresh_val and in_line:
            in_line = False
            h = y - start_y
            if h >= 10: # Minimum line height filtering
                lines.append((start_y, y))

    if in_line and (binarised_img.shape[0] - start_y) >= 10:
        lines.append((start_y, binarised_img.shape[0]))

    width = binarised_img.shape[1]
    line_regions = []

    for y1, y2 in lines:
        line_regions.append({
            "bbox": [0, y1, width, y2 - y1],
            "page_number": page_number
        })

    return line_regions
