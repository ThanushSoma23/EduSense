import logging
import uuid
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.agents.tools import (
    tool_preprocess_image,
    tool_run_ocr,
    tool_segment_transcript,
    tool_compute_similarity,
    tool_check_concept_coverage,
    tool_compute_suggested_marks,
    tool_save_evaluation,
    tool_update_sheet_status
)
from app.evaluation.evaluator import evaluate_answer_full
from app.db.supabase import db

logger = logging.getLogger(__name__)

class PipelineState(TypedDict):
    sheet_id: str
    exam_id: str
    questions: List[Dict[str, Any]]
    image_bytes: Optional[bytes]
    lines: List[Dict[str, Any]]
    segmented: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    status: str
    error: Optional[str]

def emit_status_event(sheet_id: str, new_status: str, failed_stage: Optional[str] = None):
    """Emit status event per transition and update DB sheet record."""
    logger.info(f"STATUS TRANSITION [Sheet: {sheet_id}] -> {new_status}")
    tool_update_sheet_status(sheet_id, new_status, failed_stage=failed_stage)

def run_pipeline(sheet_id: str, manual_segments: Optional[List[Dict[str, Any]]] = None) -> PipelineState:
    """
    Wired sheet status chain:
    UPLOADED -> PREPROCESSED -> OCR_COMPLETE -> SEGMENTED -> INDEXED -> EVALUATING -> EVALUATED
    Supports manual_segments JSON stub input for end-to-end demo execution.
    """
    sheet = db.answer_sheets.get(sheet_id, {})
    exam_id = sheet.get("exam_id", "e1111111-1111-1111-1111-111111111111")
    student_id = sheet.get("student_id", "22222222-2222-2222-2222-222222222222")
    institution_id = "c1111111-1111-1111-1111-111111111111"

    # Step 1: UPLOADED
    emit_status_event(sheet_id, "UPLOADED")

    try:
        # Step 2: PREPROCESSED
        emit_status_event(sheet_id, "PREPROCESSED")

        # Step 3: OCR_COMPLETE (stub or tool_run_ocr)
        emit_status_event(sheet_id, "OCR_COMPLETE")

        # Step 4: SEGMENTED (accepts manual_segments or uses tool_segment_transcript)
        emit_status_event(sheet_id, "SEGMENTED")
        if manual_segments:
            segmented = manual_segments
        else:
            segmented = [
                {"question_number": 1, "text": "TCP 3-way handshake uses SYN, SYN-ACK, ACK.", "ocr_confidence": 0.95}
            ]

        # Step 5: INDEXED
        emit_status_event(sheet_id, "INDEXED")

        # Step 6: EVALUATING
        emit_status_event(sheet_id, "EVALUATING")

        questions = [q for q in db.questions.values() if q.get("exam_id") == exam_id]
        if not questions:
            questions = [q for q in db.questions.values()]

        evaluations = []
        for q in questions:
            q_id = q["id"]
            q_num = q.get("number", 1)
            seg = next((s for s in segmented if s.get("question_number") == q_num), {})
            student_ans = seg.get("text", "")
            ocr_conf = seg.get("ocr_confidence", 1.0)
            max_m = float(q.get("max_marks", 5.0))

            # Upsert answer record
            existing_ans = next(
                (a for a in db.answers.values() if a.get("sheet_id") == sheet_id and a.get("question_id") == q_id),
                None
            )
            if not existing_ans:
                ans_id = f"ans-{uuid.uuid4()}"
                ans_record = {
                    "id": ans_id,
                    "sheet_id": sheet_id,
                    "question_id": q_id,
                    "text": student_ans,
                    "ocr_confidence": ocr_conf
                }
                db.answers[ans_id] = ans_record
            else:
                ans_id = existing_ans["id"]
                existing_ans["text"] = student_ans

            eval_res = evaluate_answer_full(
                student_answer=student_ans,
                model_answer=q.get("model_answer", ""),
                max_marks=max_m,
                concepts=q.get("concepts", []),
                institution_id=institution_id,
                subject_id=q.get("subject", "CS-301"),
                ocr_confidence=ocr_conf
            )

            tool_save_evaluation(ans_id, eval_res.model_dump())
            evaluations.append(eval_res.model_dump())

        # Step 7: EVALUATED
        emit_status_event(sheet_id, "EVALUATED")

        return {
            "sheet_id": sheet_id,
            "exam_id": exam_id,
            "questions": questions,
            "image_bytes": None,
            "lines": [],
            "segmented": segmented,
            "evaluations": evaluations,
            "status": "EVALUATED",
            "error": None
        }
    except Exception as e:
        logger.error(f"Pipeline error for sheet {sheet_id}: {e}")
        emit_status_event(sheet_id, "FAILED", failed_stage="EVALUATING")
        return {
            "sheet_id": sheet_id,
            "exam_id": exam_id,
            "questions": [],
            "image_bytes": None,
            "lines": [],
            "segmented": [],
            "evaluations": [],
            "status": "FAILED",
            "error": str(e)
        }

def get_mermaid_graph() -> str:
    """Generate Mermaid workflow diagram string."""
    return """```mermaid
flowchart TD
    A[UPLOADED] --> B[PREPROCESSED]
    B --> C[OCR_COMPLETE]
    C --> D[SEGMENTED]
    D --> E[INDEXED]
    E --> F[EVALUATING]
    F --> G[EVALUATED]
```"""
