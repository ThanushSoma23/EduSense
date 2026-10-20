"""
AIML-2: Handwritten OCR & Question Segmentation
EduSense AI System
"""

from .ocr import extract_text_from_sheet, recognize_single_image, load_trocr
from .segmentation import segment_text, segment_ocr_lines, extract_question_marker
from .confidence import calculate_token_confidence, check_needs_review
from .pipeline import transcribe

__all__ = [
    "extract_text_from_sheet",
    "recognize_single_image",
    "load_trocr",
    "segment_text",
    "segment_ocr_lines",
    "extract_question_marker",
    "calculate_token_confidence",
    "check_needs_review",
    "transcribe"
]
