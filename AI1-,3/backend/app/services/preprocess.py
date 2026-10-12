import logging
import numpy as np

logger = logging.getLogger(__name__)

def preprocess_image(image_bytes: bytes) -> bytes:
    """
    OpenCV image enhancement pipeline:
    Grayscale -> Denoise -> Deskew -> CLAHE -> Adaptive Binarization
    """
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Failed to decode image bytes into OpenCV matrix. Returning original bytes.")
            return image_bytes

        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)

        # 4. Adaptive Thresholding / Binarization
        binarized = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Encode back to JPEG image bytes
        success, encoded = cv2.imencode('.jpg', binarized)
        if success:
            return encoded.tobytes()
        return image_bytes
    except Exception as e:
        logger.error(f"OpenCV Preprocessing failed: {e}. Returning raw image bytes.")
        return image_bytes
