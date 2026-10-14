"""
EduSense — OCR & Question Segmentation Service Integration
Bridges the AIML-2 handwritten TrOCR engine and regex segmentation parser
into the primary PostgreSQL backend application lifecycle.
"""

import re
import io
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("app.services.ocr_service")

# Comprehensive regex pattern covering standard handwritten question markers:
# Matches:
#   - Q1, Q1:, Q1., Q-1, Q 1, Q.1
#   - Question 1, Question 1:, Question-1
#   - Ans 1:, Answer 1:, Ans. 1
#   - 1., 1), 1: at start of line
QUESTION_HEADER_PATTERN = re.compile(
    r'^(?:(?:Q|Question|Ans|Answer|\#)\s*[\.\-]?\s*(\d+)[\.\:\)\-]?|(\d+)[\.\:\)\-])\s*',
    re.IGNORECASE
)


def extract_question_number_and_body(text: str) -> Optional[Tuple[int, str]]:
    """
    Check if a text line starts with a recognizable question marker.
    Returns (question_number, remaining_body_text) if matched, else None.
    """
    stripped = text.strip()
    match = QUESTION_HEADER_PATTERN.match(stripped)
    if not match:
        return None

    q_str = match.group(1) or match.group(2)
    try:
        q_num = int(q_str)
    except (ValueError, TypeError):
        return None

    body = stripped[match.end():].strip()
    return q_num, body


def get_mock_ocr_lines() -> List[Dict[str, Any]]:
    """Deterministic mock OCR output for test suites and offline operation."""
    return [
        {"text": "Q1 Explain deadlock. Deadlock occurs when processes wait for resources held by each other.", "confidence": 0.94},
        {"text": "A deadlock condition requires mutual exclusion, hold and wait, no preemption, and circular wait.", "confidence": 0.92},
        {"text": "Q2 What is a process? A process is a program in execution containing its own address space.", "confidence": 0.88},
        {"text": "Q3 Explain semaphore. Semaphore is used for synchronization.", "confidence": 0.52}
    ]


def run_trocr_inference(image_bytes: bytes) -> Optional[List[Dict[str, Any]]]:
    """
    Attempts to run real Microsoft TrOCR inference on image bytes.
    Returns None if model/weights/dependencies are unavailable.
    """
    if not image_bytes:
        return None

    try:
        from PIL import Image
        import numpy as np

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Try importing AIML-2 module if present
        try:
            import sys
            from pathlib import Path
            aiml2_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "AIML-2")
            if aiml2_dir not in sys.path:
                sys.path.insert(0, aiml2_dir)
            from ocr import extract_text_from_sheet
            lines = extract_text_from_sheet(img, use_mock_fallback=False)
            if lines:
                return lines
        except Exception as e:
            logger.debug(f"Direct AIML-2 import unavailable ({e}), trying standard TrOCR loader.")

        return None
    except Exception as e:
        logger.warning(f"TrOCR execution error: {e}")
        return None


def segment_ocr_lines(
    ocr_lines: List[Dict[str, Any]],
    threshold: float = 0.70
) -> List[Dict[str, Any]]:
    """
    Segments OCR line items into question-wise answers with confidence calculation
    and needs_review decision.
    """
    if not ocr_lines:
        return []

    segmented: List[Dict[str, Any]] = []
    current_q_num: int = 1
    current_lines: List[str] = []
    current_confs: List[float] = []
    has_seen_header: bool = False

    def finalize_block(q_num: int, lines: List[str], confs: List[float]) -> Dict[str, Any]:
        combined_text = " ".join(lines).strip()
        if not combined_text:
            return {
                "question_number": q_num,
                "text": "",
                "confidence": 0.0,
                "needs_review": True
            }

        avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.90
        min_conf = min(confs) if confs else 1.0
        needs_rev = (avg_conf < threshold) or (min_conf < 0.50) or (len(combined_text) < 5)

        return {
            "question_number": q_num,
            "text": combined_text,
            "confidence": avg_conf,
            "needs_review": needs_rev
        }

    for item in ocr_lines:
        text = str(item.get("text", "")).strip()
        conf = float(item.get("confidence", 0.90))
        if not text:
            continue

        marker = extract_question_number_and_body(text)
        if marker:
            q_num, body = marker
            if current_lines or has_seen_header:
                segmented.append(finalize_block(current_q_num, current_lines, current_confs))
            current_q_num = q_num
            has_seen_header = True
            current_lines = [body] if body else []
            current_confs = [conf]
        else:
            current_lines.append(text)
            current_confs.append(conf)

    if current_lines or has_seen_header:
        segmented.append(finalize_block(current_q_num, current_lines, current_confs))

    return segmented


def transcribe_and_segment(
    image_bytes: bytes,
    threshold: float = 0.70,
    backend: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Main transcription service entry point:
    1. Runs OCR (TrOCR if available and requested, otherwise deterministic mock).
    2. Segments extracted text into question-wise answers.
    3. Returns (segmented_answers, backend_used).
    """
    backend_choice = (backend or "auto").lower()

    if backend_choice == "mock":
        raw_lines = get_mock_ocr_lines()
        backend_used = "mock"
    else:
        # Try real TrOCR
        trocr_lines = run_trocr_inference(image_bytes)
        if trocr_lines:
            raw_lines = trocr_lines
            backend_used = "trocr"
        else:
            raw_lines = get_mock_ocr_lines()
            backend_used = "mock"

    segmented = segment_ocr_lines(raw_lines, threshold=threshold)
    return segmented, backend_used
