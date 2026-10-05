import re
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

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

def extract_question_number_and_body(text: str) -> Optional[tuple[int, str]]:
    """
    Check if a text line starts with a question marker.
    Returns (question_number, remaining_body_text) if matched, else None.
    """
    stripped = text.strip()
    match = QUESTION_HEADER_PATTERN.match(stripped)
    if not match:
        return None

    # Group 1 captures (Q/Question/Ans prefix), Group 2 captures pure digits (e.g. '1.')
    q_str = match.group(1) or match.group(2)
    try:
        q_num = int(q_str)
    except (ValueError, TypeError):
        return None

    body = stripped[match.end():].strip()
    return q_num, body

def segment_transcript(
    ocr_lines: List[Dict[str, Any]],
    review_threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Per-question segmentation parser:
    1. Groups consecutive OCR lines by question marker headers.
    2. Strips question prefixes to preserve pure student answer body.
    3. Computes aggregated OCR confidence per question.
    4. Evaluates needs_review boolean flag based on review_threshold.
    """
    if not ocr_lines:
        return []

    threshold = review_threshold if review_threshold is not None else settings.OCR_REVIEW_THRESHOLD

    segmented_questions: List[Dict[str, Any]] = []
    current_q_num: int = 1
    current_lines: List[str] = []
    current_confidences: List[float] = []
    has_seen_header = False

    for line in ocr_lines:
        text = line.get("text", "").strip()
        conf = float(line.get("confidence", 1.0))
        if not text:
            continue

        header_match = extract_question_number_and_body(text)

        if header_match:
            q_idx, clean_body = header_match

            # If we were already accumulating an answer, finalize it
            if current_lines or has_seen_header:
                avg_conf = round(sum(current_confidences) / len(current_confidences), 4) if current_confidences else 1.0
                min_conf = min(current_confidences) if current_confidences else 1.0
                ans_text = " ".join(current_lines).strip()
                needs_rev = (avg_conf < threshold) or (min_conf < 0.50) or (len(ans_text) < 5)

                segmented_questions.append({
                    "question_number": current_q_num,
                    "text": ans_text,
                    "ocr_confidence": avg_conf,
                    "needs_review": needs_rev
                })

            current_q_num = q_idx
            has_seen_header = True
            current_lines = [clean_body] if clean_body else []
            current_confidences = [conf]
        else:
            current_lines.append(text)
            current_confidences.append(conf)

    # Finalize the last accumulated question
    if current_lines or has_seen_header:
        avg_conf = round(sum(current_confidences) / len(current_confidences), 4) if current_confidences else 1.0
        min_conf = min(current_confidences) if current_confidences else 1.0
        ans_text = " ".join(current_lines).strip()
        needs_rev = (avg_conf < threshold) or (min_conf < 0.50) or (len(ans_text) < 5)

        segmented_questions.append({
            "question_number": current_q_num,
            "text": ans_text,
            "ocr_confidence": avg_conf,
            "needs_review": needs_rev
        })

    return segmented_questions
