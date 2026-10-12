from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from typing import Dict, Any, List, Optional
from app.core.security import get_current_user, require_teacher, require_active_user
from app.core.rate_limiter import auth_rate_limiter
from app.db.supabase import db
from app.agents.tools import tool_index_document, tool_update_sheet_status
from app.evaluation.evaluator import evaluate_answer_full

router = APIRouter(prefix="/evaluate", tags=["Evaluation & Knowledge Base"])
kb_router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

ALLOWED_MAGIC_BYTES = [
    b"%PDF", # PDF
    b"\x50\x4b\x03\x04", # DOCX/ZIP
]

@router.post("/{sheet_id}")
def trigger_sheet_evaluation(
    sheet_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    """Trigger batch evaluation for an answer sheet (Teacher-only)."""
    # Rate limit check
    auth_rate_limiter.check_rate_limit(request)

    sheet = db.answer_sheets.get(sheet_id)
    if not sheet:
        raise HTTPException(status_code=404, detail="Answer sheet not found.")

    exam_id = sheet.get("exam_id", "")
    exam = db.exams.get(exam_id, {})
    institution_id = current_user.get("college_id", "c1111111-1111-1111-1111-111111111111")
    subject_id = exam.get("subject", "Computer Science")

    tool_update_sheet_status(sheet_id, "EVALUATING")

    # Fetch answers associated with sheet
    sheet_answers = [a for a in db.answers.values() if a.get("sheet_id") == sheet_id]
    evaluations_created = []

    for ans in sheet_answers:
        q_id = ans.get("question_id")
        question = db.questions.get(q_id, {})
        student_ans = ans.get("text", "")
        model_ans = question.get("model_answer", "")
        max_m = float(question.get("max_marks", 5.0))
        concepts = question.get("concepts", [])

        eval_res = evaluate_answer_full(
            student_answer=student_ans,
            model_answer=model_ans,
            max_marks=max_m,
            concepts=concepts,
            institution_id=institution_id,
            subject_id=subject_id,
            ocr_confidence=ans.get("ocr_confidence", 1.0)
        )

        eval_id = f"ev-{ans['id']}"
        eval_dict = eval_res.model_dump()
        db.evaluations[eval_id] = {
            "id": eval_id,
            "answer_id": ans["id"],
            "similarity_percent": eval_dict["similarity_pct"],
            "concepts": eval_dict["covered"] + eval_dict["partial"] + eval_dict["missing"],
            "suggested_marks_min": eval_dict["ai_suggested_min"],
            "suggested_marks_max": eval_dict["ai_suggested_max"],
            "confidence": eval_dict["ai_confidence"],
            "reason": eval_dict["rationale"],
            "citations": eval_dict["citations"],
            "flags": eval_dict["flags"]
        }
        evaluations_created.append(db.evaluations[eval_id])

    tool_update_sheet_status(sheet_id, "EVALUATED")

    return {
        "status": "success",
        "sheet_id": sheet_id,
        "evaluations_count": len(evaluations_created),
        "sheet_status": "EVALUATED"
    }

@router.get("/{sheet_id}/result")
def get_evaluation_results(
    sheet_id: str,
    current_user: Dict[str, Any] = Depends(require_active_user)
) -> Dict[str, Any]:
    """Get evaluation results for an answer sheet."""
    sheet = db.answer_sheets.get(sheet_id)
    if not sheet:
        raise HTTPException(status_code=404, detail="Answer sheet not found.")

    # Student access check: sheet must belong to student and exam must be published
    if current_user.get("role") == "student":
        if sheet.get("student_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied to another student's answer sheet.")

        exam_id = sheet.get("exam_id")
        publication = next((p for p in db.publications.values() if p.get("exam_id") == exam_id), None)
        if not publication:
            raise HTTPException(status_code=403, detail="Results not yet published by teacher.")

    sheet_answers = [a for a in db.answers.values() if a.get("sheet_id") == sheet_id]
    ans_ids = {a["id"] for a in sheet_answers}

    results = [e for e in db.evaluations.values() if e.get("answer_id") in ans_ids]

    return {
        "sheet_id": sheet_id,
        "status": sheet.get("status", "ready"),
        "results": results
    }

@kb_router.post("/upload")
async def upload_kb_document(
    request: Request,
    file: UploadFile = File(...),
    subject_id: str = "CS-301",
    current_user: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    """Upload document to Knowledge Base (Teacher-only). Checks magic bytes and max size (10MB)."""
    auth_rate_limiter.check_rate_limit(request)

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    # Magic byte check for PDF / DOCX or fallback plain text check
    is_valid_magic = any(file_bytes.startswith(magic) for magic in ALLOWED_MAGIC_BYTES)
    if not is_valid_magic and not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Unsupported file format. Only PDF, DOCX, and TXT files are accepted.")

    institution_id = current_user.get("college_id", "c1111111-1111-1111-1111-111111111111")
    index_res = tool_index_document(
        file_bytes=file_bytes,
        filename=file.filename or "uploaded_doc.pdf",
        subject_id=subject_id,
        institution_id=institution_id
    )

    return {
        "message": f"Document '{file.filename}' indexed successfully into Knowledge Base.",
        "indexing": index_res
    }
