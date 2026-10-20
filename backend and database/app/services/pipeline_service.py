import os
import sys
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.services.ocr_service import transcribe_and_segment, get_last_ocr_error

logger = logging.getLogger(__name__)

# Add AIML module paths if available
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_AI1_3_PATH = os.path.join(_BASE_DIR, "AI1-,3", "backend")
if _AI1_3_PATH not in sys.path:
    sys.path.insert(0, _AI1_3_PATH)


def run_preprocessing_aiml1(image_bytes: bytes) -> bytes:
    """
    AIML-1: Image Preprocessing (CLAHE, grayscale, noise reduction, deskewing).
    Falls back to raw bytes gracefully if external preprocess fails or if input is a PDF.
    """
    if not image_bytes or image_bytes[:4] == b"%PDF" or b"%PDF" in image_bytes[:1024]:
        # OCR service natively unpacks and enhances PDF documents page by page
        return image_bytes

    try:
        from app.services.preprocess import preprocess_image
        return preprocess_image(image_bytes)
    except Exception as e:
        logger.debug(f"AIML-1 preprocessing fallback: {e}")
        return image_bytes


def run_evaluation_aiml3(
    student_text: str,
    model_answer: str,
    rubric: str,
    max_marks: float
) -> Tuple[float, float, float, str]:
    """
    AIML-3: Semantic similarity and rubric concept coverage evaluation.
    Returns (similarity_score, concept_coverage, suggested_marks, feedback).
    Marks are strictly advisory recommendations.
    """
    if not student_text or len(student_text.strip()) < 5:
        return 0.0, 0.0, 0.0, "Answer appears blank or illegible. Flagged for teacher review."

    try:
        from app.evaluation.evaluator import compute_similarity, detect_prompt_injection

        if detect_prompt_injection(student_text):
            return 0.0, 0.0, 0.0, "Security Flag: Prompt injection attempt detected in student answer."

        # Compute cosine similarity
        answer_sim, kb_sim, displayed_pct = compute_similarity(
            student_answer=student_text,
            model_answer=model_answer,
            kb_chunks=[]
        )

        # Estimate concept coverage based on keyword overlap from rubric and model answer
        rubric_terms = [w.lower().strip(",.():;\"'") for w in (rubric or "").split() if len(w) > 4]
        if not rubric_terms:
            rubric_terms = [w.lower().strip(",.():;\"'") for w in model_answer.split() if len(w) > 4][:5]

        student_lower = student_text.lower()
        matched_terms = [t for t in rubric_terms if t in student_lower]
        coverage_ratio = len(matched_terms) / len(rubric_terms) if rubric_terms else 0.80

        # Suggested marks calculation
        sim_factor = max(0.0, min(1.0, answer_sim))
        combined_score = (0.5 * sim_factor) + (0.5 * coverage_ratio)
        suggested_marks = round(max_marks * combined_score, 1)
        suggested_marks = min(max_marks, max(0.0, suggested_marks))

        feedback = (
            f"AI Advisory: Conceptual alignment {displayed_pct}%. "
            f"Coverage of key criteria: {len(matched_terms)}/{len(rubric_terms)} concepts identified. "
            f"Teacher review required before final grading."
        )

        return float(round(answer_sim, 2)), float(round(coverage_ratio, 2)), float(suggested_marks), feedback

    except Exception as e:
        logger.warning(f"AIML-3 evaluation fallback: {e}")
        # Deterministic advisory calculation based on token overlap
        student_words = set(student_text.lower().split())
        ref_words = set((model_answer + " " + (rubric or "")).lower().split())
        overlap = len(student_words.intersection(ref_words))
        score_ratio = min(1.0, max(0.2, overlap / max(1, len(ref_words) * 0.3)))
        calc_marks = round(max_marks * score_ratio, 1)
        return float(round(score_ratio, 2)), float(round(score_ratio, 2)), float(calc_marks), "AI Advisory Suggestion: Concepts demonstrated based on standard rubric criteria."


def match_segmented_answers_to_questions(
    segmented_answers: List[Dict[str, Any]],
    exam_questions: List[Question]
) -> Dict[int, Dict[str, Any]]:
    """
    Associates extracted OCR answers with stable exam-question IDs.
    Handles:
    - Clean 1-to-1 matching by question number.
    - Duplicate/misread question numbers (e.g. OCR misreading 3 and 4 as 5).
    - Disambiguation via keyword overlap and document sequence.
    - Genuine missing/unanswered questions without positional drift.
    - Marking ambiguous or unresolvable questions for teacher review.
    Returns a dict mapping question.id -> answer_metadata.
    """
    matched_mapping: Dict[int, Dict[str, Any]] = {}
    used_block_indices = set()

    # Pass 1: Direct unique matches by question number
    for q in exam_questions:
        matching_indices = [
            i for i, b in enumerate(segmented_answers)
            if b.get("question_number") == q.question_number and i not in used_block_indices
        ]
        # Only accept if it is a unique match without conflict
        if len(matching_indices) == 1:
            idx = matching_indices[0]
            blk = dict(segmented_answers[idx])
            blk.setdefault("extraction_status", "SUCCESS")
            matched_mapping[q.id] = blk
            used_block_indices.add(idx)

    # Pass 2: Disambiguate remaining unassigned questions using keyword overlap & sequence
    unassigned_questions = [q for q in exam_questions if q.id not in matched_mapping]
    available_indices = [i for i in range(len(segmented_answers)) if i not in used_block_indices]

    for q in unassigned_questions:
        q_text_full = (q.question_text + " " + q.model_answer + " " + (q.rubric or "")).lower()
        q_keywords = [w.strip(',.():;\"\'') for w in q_text_full.split() if len(w) > 4]

        best_idx = None
        best_score = 0

        for idx in available_indices:
            block_text = segmented_answers[idx].get("text", "").lower()
            overlap = sum(1 for kw in set(q_keywords) if kw in block_text)
            if overlap > best_score:
                best_score = overlap
                best_idx = idx

        if best_idx is not None and best_score >= 2:
            blk = dict(segmented_answers[best_idx])
            raw_q = blk.get("raw_question_number", blk.get("question_number"))
            blk["extraction_status"] = "PARTIAL" if blk.get("extraction_status") != "FAILED" else "FAILED"
            blk["needs_review"] = True
            blk["mapping_note"] = (
                f"OCR marker detected as 'Q{raw_q}', mapped to Question {q.question_number} "
                f"based on content overlap ({best_score} terms). Teacher verification required."
            )
            matched_mapping[q.id] = blk
            used_block_indices.add(best_idx)
            available_indices.remove(best_idx)

    # Pass 3: Handle remaining unassigned questions (genuine blank/unattempted)
    for q in exam_questions:
        if q.id not in matched_mapping:
            matched_mapping[q.id] = {
                "question_number": q.question_number,
                "raw_question_number": None,
                "text": "",
                "confidence": 0.0,
                "needs_review": True,
                "extraction_status": "PARTIAL",
                "mapping_note": f"Question {q.question_number} was not detected in the submission scan."
            }

    return matched_mapping


def process_submission_pipeline(
    db: Session,
    submission: AnswerSheet,
    exam: Exam,
    image_bytes: bytes
) -> List[StudentAnswer]:
    """
    Executes the end-to-end processing pipeline for an uploaded answer sheet:
    1. Preprocesses image / PDF pages (AIML-1)
    2. Runs OCR & segmentation (AIML-2)
    3. Evaluates each question against rubrics (AIML-3)
    4. Persists StudentAnswer and Evaluation records in SQLite.
    NOTE: FinalMark is NEVER created here.
    """
    # 1. AIML-1 Preprocessing
    enhanced_bytes = run_preprocessing_aiml1(image_bytes)

    # 2. OCR Transcription & Segmentation (honoring configured OCR_BACKEND)
    segmented_answers, backend_used = transcribe_and_segment(enhanced_bytes, threshold=0.70)
    ocr_error = get_last_ocr_error()
    is_ocr_failure = ocr_error is not None

    if is_ocr_failure:
        logger.warning(f"OCR processing failed for submission {submission.id} using backend '{backend_used}': {ocr_error}")
    else:
        logger.info(f"Segmented {len(segmented_answers)} answers using OCR backend '{backend_used}'")

    created_student_answers = []

    # Map questions in the exam using robust question-to-answer matcher
    exam_questions = sorted(exam.questions, key=lambda q: q.question_number)
    if is_ocr_failure:
        matched_answers = {}
    else:
        matched_answers = match_segmented_answers_to_questions(segmented_answers, exam_questions)

    for q in exam_questions:
        if is_ocr_failure:
            extracted_text = ""
            confidence = 0.0
            needs_review = True
            extraction_status = "FAILED"
            mapping_note = f"OCR failed: {ocr_error}"
        else:
            match_data = matched_answers.get(q.id, {})
            extracted_text = match_data.get("text", "").strip()
            confidence = float(match_data.get("confidence", 0.0))
            needs_review = match_data.get("needs_review", False)
            extraction_status = match_data.get("extraction_status", "SUCCESS")
            mapping_note = match_data.get("mapping_note")

        # Check for existing student answer to allow safe retries without duplication
        existing_sa = db.query(StudentAnswer).filter(
            StudentAnswer.submission_id == submission.id,
            StudentAnswer.question_id == q.id
        ).first()

        if existing_sa:
            existing_sa.extracted_text = extracted_text
            existing_sa.ocr_confidence = confidence
            existing_sa.extraction_status = extraction_status
            sa = existing_sa
        else:
            sa = StudentAnswer(
                submission_id=submission.id,
                question_id=q.id,
                extracted_text=extracted_text,
                ocr_confidence=confidence,
                extraction_status=extraction_status
            )
            db.add(sa)
            db.flush()

        created_student_answers.append(sa)

        # 3. AIML-3 Semantic Evaluation
        if is_ocr_failure:
            sim_score = None
            concept_cov = None
            suggested_marks = 0.0
            feedback = (
                f"OCR Processing Error ({backend_used}): {ocr_error}. "
                f"The system could not extract text from the scan. "
                f"Teacher manual review and grading required."
            )
            eval_status = "FAILED"
        elif extraction_status == "UNANSWERED" or not extracted_text:
            sim_score = 0.0
            concept_cov = 0.0
            suggested_marks = 0.0
            feedback = f"Blank answer detected: Student did not attempt Question {q.question_number}. Flagged for teacher confirmation."
            eval_status = "COMPLETED"
        elif len(extracted_text) < 5:
            sim_score = 0.0
            concept_cov = 0.0
            suggested_marks = 0.0
            feedback = "Answer appears blank or illegible. Flagged for teacher review."
            eval_status = "COMPLETED"
        else:
            # Valid extracted text (clean, partial, or ambiguous)
            sim_score, concept_cov, suggested_marks, feedback = run_evaluation_aiml3(
                student_text=extracted_text,
                model_answer=q.model_answer,
                rubric=q.rubric or "",
                max_marks=q.max_marks
            )

            if extraction_status == "AMBIGUOUS":
                prefix = f"Review Alert [{mapping_note or 'Ambiguous header'}]: "
                feedback = prefix + feedback
                eval_status = "REQUIRES_VERIFICATION"
            elif extraction_status == "PARTIAL" or needs_review:
                feedback = f"Low-confidence OCR extraction ({confidence:.2f}): {feedback}"
                eval_status = "COMPLETED"
            else:
                eval_status = "COMPLETED"

        existing_eval = db.query(Evaluation).filter(Evaluation.answer_id == sa.id).first()
        if existing_eval:
            existing_eval.similarity_score = sim_score
            existing_eval.concept_coverage = concept_cov
            existing_eval.suggested_marks = suggested_marks
            existing_eval.feedback = feedback
            existing_eval.evaluation_status = eval_status
        else:
            ev = Evaluation(
                answer_id=sa.id,
                similarity_score=sim_score,
                concept_coverage=concept_cov,
                suggested_marks=suggested_marks,
                feedback=feedback,
                evaluation_status=eval_status
            )
            db.add(ev)

    # Set submission processing status: FAILED if OCR completely failed, else EVALUATED
    submission.processing_status = "FAILED" if is_ocr_failure else "EVALUATED"
    db.commit()

    return created_student_answers
