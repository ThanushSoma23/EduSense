import cv2
import numpy as np

def denoise_and_remove_shadows(img: np.ndarray) -> np.ndarray:
    """
    Remove uneven lighting/shadows using morphological close + divide,
    and apply fastNlMeans or median filtering tuned NOT to erase thin pen strokes.
    """
    if img is None or img.size == 0:
        return img

    is_color = len(img.shape) == 3
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if is_color else img

    # Background shadow removal via morphological close & divide
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    divided = cv2.divide(gray, background, scale=255)

    # Median blur preserving stroke edges
    denoised = cv2.medianBlur(divided, 3)

    if is_color:
        return cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
    return denoised
