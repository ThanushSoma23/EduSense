import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.services.preprocess import preprocess_image
from app.services.ocr import run_ocr
from app.services.segmentation import segment_transcript
from app.evaluation.evaluator import evaluate_answer_full, compute_similarity as eval_sim, compute_marks_range as eval_marks_range
from app.evaluation.rag_kb import index_document as kb_index_doc, hybrid_retrieve
from app.db.supabase import db

logger = logging.getLogger(__name__)

# HARD INVARIANT: NO tool in tools.py may read, update, or write to table 'marks' or field 'final_marks'.

def tool_preprocess_image(image_bytes: bytes) -> bytes:
    """Preprocess scanned image bytes via OpenCV."""
    return preprocess_image(image_bytes)

def tool_run_ocr(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Run OCR handwriting recognition engine."""
    return run_ocr(image_bytes)

def tool_segment_transcript(ocr_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Segment transcript lines into per-question text and confidence."""
    return segment_transcript(ocr_lines)

def tool_compute_similarity(student_answer: str, model_answer: str) -> float:
    """Compute semantic cosine similarity between student answer and model answer."""
    ans_sim, _, displayed_pct = eval_sim(student_answer, model_answer, [])
    return displayed_pct

def tool_check_concept_coverage(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run batched concept coverage evaluation across questions."""
    results = []
    for item in items:
        q_id = item.get("question_id", "")
        student_ans = item.get("student_answer", "")
        model_ans = item.get("model_answer", "")
        concepts = item.get("concepts", [])

        eval_res = evaluate_answer_full(
            student_answer=student_ans,
            model_answer=model_ans,
            max_marks=float(item.get("max_marks", 5.0)),
            concepts=concepts,
            institution_id="c1111111-1111-1111-1111-111111111111",
            subject_id="CS-301"
        )
        results.append({
            "question_id": q_id,
            "concepts": eval_res.covered + eval_res.partial + eval_res.missing,
            "reason": eval_res.rationale
        })
    return results

def tool_compute_suggested_marks(concepts: List[Dict[str, Any]], max_marks: float, confidence: float) -> Tuple[float, float]:
    """Compute deterministic suggested marks range."""
    # Compute coverage score
    total_w = sum(float(c.get("weight", 1.0)) for c in concepts) or 1.0
    weighted_score = sum(float(c.get("weight", 1.0)) * (1.0 if c.get("status") == "covered" else (0.5 if c.get("status") == "partial" else 0.0)) for c in concepts)
    cov = weighted_score / total_w

    s_min, s_max, _ = eval_marks_range(cov, max_marks, confidence)
    return s_min, s_max

def tool_retrieve_reference_chunks(query: str, subject_id: str, institution_id: str, k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve top-k relevant reference chunks from kb_chunks table via hybrid retrieval."""
    return hybrid_retrieve(query=query, subject_id=subject_id, institution_id=institution_id, k=k)

def tool_index_document(file_bytes: bytes, filename: str, subject_id: str, institution_id: str) -> Dict[str, Any]:
    """Index document into Knowledge Base."""
    return kb_index_doc(file_bytes=file_bytes, filename=filename, subject_id=subject_id, institution_id=institution_id)

def tool_evaluate_answer(
    student_answer: str,
    model_answer: str,
    max_marks: float,
    concepts: List[Dict[str, Any]],
    institution_id: str,
    subject_id: str,
    ocr_confidence: float = 1.0
) -> Dict[str, Any]:
    """Run AIML-3 evaluation pipeline for a single answer."""
    res = evaluate_answer_full(
        student_answer=student_answer,
        model_answer=model_answer,
        max_marks=max_marks,
        concepts=concepts,
        institution_id=institution_id,
        subject_id=subject_id,
        ocr_confidence=ocr_confidence
    )
    return res.model_dump()

def tool_save_evaluation(answer_id: str, evaluation_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist evaluation suggestions ONLY to the evaluations table.
    STRICTLY FORBIDDEN FROM WRITING TO MARKS OR SETTING FINAL_MARKS.
    """
    eval_id = f"ev-{uuid.uuid4()}"
    eval_record = {
        "id": eval_id,
        "answer_id": answer_id,
        "similarity_percent": evaluation_dict.get("similarity_pct", 0.0),
        "concepts": evaluation_dict.get("covered", []) + evaluation_dict.get("partial", []) + evaluation_dict.get("missing", []),
        "covered": evaluation_dict.get("covered", []),
        "partial": evaluation_dict.get("partial", []),
        "missing": evaluation_dict.get("missing", []),
        "keywords_missing": evaluation_dict.get("keywords_missing", []),
        "suggested_marks_min": evaluation_dict.get("ai_suggested_min", 0.0),
        "suggested_marks_max": evaluation_dict.get("ai_suggested_max", 0.0),
        "confidence": evaluation_dict.get("ai_confidence", 1.0),
        "reason": evaluation_dict.get("rationale", ""),
        "citations": evaluation_dict.get("citations", []),
        "flags": evaluation_dict.get("flags", [])
    }
    db.evaluations[eval_id] = eval_record
    logger.info(f"Persisted AI evaluation suggestion for answer_id {answer_id}.")
    return eval_record

def tool_update_sheet_status(sheet_id: str, status: str, error: Optional[str] = None, failed_stage: Optional[str] = None) -> Dict[str, Any]:
    """Update status of answer sheet with resumable state recording."""
    sheet = db.answer_sheets.get(sheet_id)
    if sheet:
        sheet["status"] = status
        if error is not None:
            sheet["error"] = error
        sheet["failed_stage"] = failed_stage
    return sheet or {}

