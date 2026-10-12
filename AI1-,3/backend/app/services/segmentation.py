import re
import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

def segment_transcript(ocr_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Per-question segmentation parser:
    Groups transcript lines by question header regex (e.g. 'Q1:', 'Question 2', '1.')
    Computes aggregated OCR confidence and sets needs_review boolean flag.
    """
    if not ocr_lines:
        return []

    segmented_questions = []
    current_q_num = 1
    current_lines = []
    current_confidences = []

    pattern = re.compile(r'^(?:Q|Question|\#)?\s*(\d+)[\.\:\)]', re.IGNORECASE)

    for line in ocr_lines:
        text = line.get("text", "").strip()
        conf = line.get("confidence", 1.0)
        match = pattern.match(text)

        if match:
            q_idx = int(match.group(1))
            if current_lines:
                avg_conf = round(sum(current_confidences) / len(current_confidences), 4) if current_confidences else 1.0
                needs_rev = avg_conf < settings.OCR_REVIEW_THRESHOLD
                segmented_questions.append({
                    "question_number": current_q_num,
                    "text": " ".join(current_lines).strip(),
                    "ocr_confidence": avg_conf,
                    "needs_review": needs_rev
                })
            current_q_num = q_idx
            # Strip the Q header prefix for clean answer body text
            clean_text = pattern.sub('', text).strip()
            current_lines = [clean_text] if clean_text else []
            current_confidences = [conf]
        else:
            current_lines.append(text)
            current_confidences.append(conf)

    if current_lines:
        avg_conf = round(sum(current_confidences) / len(current_confidences), 4) if current_confidences else 1.0
        needs_rev = avg_conf < settings.OCR_REVIEW_THRESHOLD
        segmented_questions.append({
            "question_number": current_q_num,
            "text": " ".join(current_lines).strip(),
            "ocr_confidence": avg_conf,
            "needs_review": needs_rev
        })

    return segmented_questions
