"""
==============================================================================
AIML-2: End-to-End Transcription & Segmentation Pipeline
Project: EduSense AI
Responsibility: Image -> TrOCR -> Question Segmentation -> Confidence -> Final JSON
==============================================================================

Pipeline Flow:
  1. Input: Cleaned Answer Sheet Image (from AIML-1)
  2. TrOCR: Extracts handwritten text and per-token generation probabilities
  3. Question Segmentation: Detects markers (Q1, Q2, Q3...) and splits answers
  4. Confidence Calculation: Computes per-question average confidence
  5. needsReview Flag: Checks if confidence < threshold or answer is blank
  6. Output: Question-wise JSON contract for AIML-3 evaluation
==============================================================================
"""

import os
from typing import Union, Dict, Any, List

try:
    from ocr import extract_text_from_sheet
    from segmentation import segment_ocr_lines
except ImportError:
    from .ocr import extract_text_from_sheet
    from .segmentation import segment_ocr_lines


def transcribe(
    image_path: Union[str, bytes, Any],
    answer_sheet_id: str = "AS001",
    threshold: float = 0.70,
    use_mock_fallback: bool = True
) -> Dict[str, Any]:
    """
    Main transcription pipeline for AIML-2.

    Parameters:
        image_path: File path to answer sheet image, or raw image bytes.
        answer_sheet_id: Identifier for the student answer sheet (e.g. 'AS001').
        threshold: Confidence threshold for needsReview flag (default: 0.70).
        use_mock_fallback: Whether to use fallback sample data if OCR returns empty.

    Returns:
        dict: Standardized question-wise JSON:
        {
            "answerSheetId": "AS001",
            "answers": [
                {
                    "questionNumber": "Q1",
                    "text": "student handwritten answer...",
                    "confidence": 0.91,
                    "needsReview": false
                },
                ...
            ]
        }
    """
    # Basic input validation
    if isinstance(image_path, str) and not os.path.exists(image_path):
        raise FileNotFoundError(f"Answer sheet image not found at: {image_path}")

    # Step 1 & 2: Extract text lines and confidence scores using TrOCR
    ocr_lines = extract_text_from_sheet(image_path, use_mock_fallback=use_mock_fallback)

    if not ocr_lines:
        return {
            "answerSheetId": answer_sheet_id,
            "answers": []
        }

    # Step 3, 4, 5: Question segmentation, per-segment confidence & needsReview flagging
    segmented_answers = segment_ocr_lines(ocr_lines, threshold=threshold)

    # Step 6: Return final standardized JSON contract
    return {
        "answerSheetId": answer_sheet_id,
        "answers": segmented_answers
    }
