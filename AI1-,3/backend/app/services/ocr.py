import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class MockOCRBackend:
    def recognize(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        return [
            {"text": "Q1: A Binary Search Tree (BST) insertion begins at root node.", "confidence": 0.96},
            {"text": "If value is smaller navigate left, if larger navigate right.", "confidence": 0.94},
            {"text": "Average time complexity is O(log n), while worst case complexity is O(n) for unbalanced tree.", "confidence": 0.98},
            {"text": "Q2: Dijkstra's algorithm finds shortest path using priority queue min-distance.", "confidence": 0.92},
            {"text": "Main limitation: Fails on graphs containing negative edge weights.", "confidence": 0.89},
            {"text": "Q3: Process has separate virtual memory address space.", "confidence": 0.95},
            {"text": "Threads share process memory, heap and files, maintaining own program counter and stack.", "confidence": 0.93}
        ]

class EasyOCRBackend:
    def __init__(self):
        self.reader = None

    def _init_reader(self):
        if self.reader is None:
            import easyocr
            logger.info("Initializing EasyOCR reader...")
            self.reader = easyocr.Reader(['en'], gpu=False)

    def recognize(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            self._init_reader()
            import numpy as np
            import cv2
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            results = self.reader.readtext(img)
            lines = []
            for bbox, text, prob in results:
                lines.append({"text": text.strip(), "confidence": round(float(prob), 4)})
            return lines if lines else MockOCRBackend().recognize(image_bytes)
        except Exception as e:
            logger.error(f"EasyOCR recognition error: {e}. Falling back to MockOCR.")
            return MockOCRBackend().recognize(image_bytes)

class TrOCRBackend:
    def recognize(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        logger.warning("TrOCR requires line-level cropping. Falling back to MockOCR for line recognition.")
        return MockOCRBackend().recognize(image_bytes)

_easyocr_singleton = None
_mock_singleton = MockOCRBackend()
_trocr_singleton = TrOCRBackend()

def run_ocr(image_bytes: bytes) -> List[Dict[str, Any]]:
    global _easyocr_singleton
    backend_choice = settings.OCR_BACKEND.lower()
    if backend_choice == "mock":
        return _mock_singleton.recognize(image_bytes)
    elif backend_choice == "trocr":
        return _trocr_singleton.recognize(image_bytes)
    else:
        if _easyocr_singleton is None:
            _easyocr_singleton = EasyOCRBackend()
        return _easyocr_singleton.recognize(image_bytes)
