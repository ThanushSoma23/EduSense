"""
==============================================================================
AIML-2: Question Segmentation Module
Project: EduSense AI
Responsibility: Segmenting OCR text / lines into individual question answers
==============================================================================

Supports question marker formats:
  - Standard: Q1, Q2, Q3
  - Spaced: Q 1, Q 2, q 1
  - Punctuated: Q.1, Q-1, Q1., Q1:, Q1-
  - Lowercase: q1, q2, q 3
  - Spelled out: Question 1, Question 2, Question-1
  - Answer prefix: Ans 1, Answer 1, Ans. 1
  - Pure numbers at start: 1., 1), 1:
==============================================================================
"""

import re
from typing import List, Dict, Any, Optional, Tuple

try:
    from confidence import check_needs_review
except ImportError:
    from .confidence import check_needs_review

# Regular expression designed for question markers at the start of a line.
# Group 1 captures the question number from prefixes like Q, Question, Ans, Answer.
# Group 2 captures the question number from pure leading digits like "1.", "1)", "1:".
QUESTION_MARKER_REGEX = re.compile(
    r'^(?:(?:q|question|ans|answer|\#)\s*[\.\-]?\s*(\d+)[\.\:\)\-]?|(\d+)[\.\:\)\-])\s*',
    re.IGNORECASE
)


def extract_question_marker(line_text: str) -> Optional[Tuple[str, str]]:
    """
    Checks if a text line starts with a recognizable question marker.

    Example inputs & outputs:
      "Q1 Explain deadlock."           -> ("Q1", "Explain deadlock.")
      "Q-2 What is a process?"         -> ("Q2", "What is a process?")
      "Question 3: Explain semaphore." -> ("Q3", "Explain semaphore.")
      "q 4 Difference between..."      -> ("Q4", "Difference between...")
      "Deadlock is a condition..."     -> None

    Returns:
      (question_number_label, remaining_text) if matched, else None.
    """
    cleaned = line_text.strip()
    if not cleaned:
        return None

    match = QUESTION_MARKER_REGEX.match(cleaned)
    if not match:
        return None

    # Determine which capture group matched the number
    num_str = match.group(1) or match.group(2)
    question_label = f"Q{num_str}"

    # Extract the remaining text after the marker
    remaining_text = cleaned[match.end():].strip()
    return question_label, remaining_text


def segment_text(raw_text: str) -> List[Dict[str, str]]:
    """
    Segments plain multi-line OCR text into question blocks.

    Input Example:
      Q1 Explain deadlock.
      Deadlock is a condition where processes wait.

      Q2 What is a process?
      A process is a program in execution.

    Output Example:
      [
        {"questionNumber": "Q1", "text": "Explain deadlock. Deadlock is a condition where processes wait."},
        {"questionNumber": "Q2", "text": "What is a process? A process is a program in execution."}
      ]
    """
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    segments: List[Dict[str, str]] = []

    current_q: str = "Q1"
    current_content: List[str] = []
    has_seen_marker: bool = False

    for line in lines:
        marker = extract_question_marker(line)
        if marker:
            q_label, rest = marker
            # If we were already collecting an answer, finalize it
            if current_content or has_seen_marker:
                combined_text = " ".join(current_content).strip()
                segments.append({
                    "questionNumber": current_q,
                    "text": combined_text
                })
            current_q = q_label
            has_seen_marker = True
            current_content = [rest] if rest else []
        else:
            current_content.append(line)

    # Finalize the last question block
    if current_content or has_seen_marker:
        combined_text = " ".join(current_content).strip()
        segments.append({
            "questionNumber": current_q,
            "text": combined_text
        })

    return segments


def segment_ocr_lines(
    ocr_lines: List[Dict[str, Any]],
    threshold: float = 0.70
) -> List[Dict[str, Any]]:
    """
    Segments structured OCR lines (with individual confidence scores)
    into question-wise answers with per-question confidence and needsReview flag.

    Parameters:
      ocr_lines: List of dicts, e.g. [{"text": "...", "confidence": 0.95}, ...]
      threshold: Minimum confidence threshold below which needsReview is True.

    Returns:
      List of question answers matching the EduSense API contract:
      [
        {
          "questionNumber": "Q1",
          "text": "Explain deadlock...",
          "confidence": 0.91,
          "needsReview": false
        },
        ...
      ]
    """
    if not ocr_lines:
        return []

    answers: List[Dict[str, Any]] = []
    current_q: str = "Q1"
    current_texts: List[str] = []
    current_confs: List[float] = []
    has_seen_marker: bool = False

    def finalize_question_block(q_num: str, texts: List[str], confs: List[float]):
        combined_text = " ".join(texts).strip()

        # Check for blank answer edge case
        if not combined_text:
            return {
                "questionNumber": q_num,
                "text": "",
                "confidence": 0.0,
                "needsReview": True
            }

        avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.90
        needs_rev = check_needs_review(avg_conf, threshold=threshold, text=combined_text)

        return {
            "questionNumber": q_num,
            "text": combined_text,
            "confidence": avg_conf,
            "needsReview": needs_rev
        }

    for item in ocr_lines:
        text = str(item.get("text", "")).strip()
        conf = float(item.get("confidence", 0.90))

        if not text:
            continue

        marker = extract_question_marker(text)
        if marker:
            q_label, rest = marker
            if current_texts or has_seen_marker:
                answer_block = finalize_question_block(current_q, current_texts, current_confs)
                answers.append(answer_block)

            current_q = q_label
            has_seen_marker = True
            current_texts = [rest] if rest else []
            current_confs = [conf]
        else:
            current_texts.append(text)
            current_confs.append(conf)

    # Finalize the last accumulated question
    if current_texts or has_seen_marker:
        answer_block = finalize_question_block(current_q, current_texts, current_confs)
        answers.append(answer_block)

    return answers
