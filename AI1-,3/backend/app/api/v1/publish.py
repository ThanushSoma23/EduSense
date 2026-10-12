import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_teacher
from app.db.supabase import db

router = APIRouter()

@router.get("/exams/{id}/publish-status")
def get_publish_status(id: str, user: dict = Depends(require_teacher)):
    exam = db.exams.get(id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")

    sheets = [s for s in db.answer_sheets.values() if s.get("exam_id") == id]
    sheet_ids = [s["id"] for s in sheets]
    answers = [a for a in db.answers.values() if a.get("sheet_id") in sheet_ids]

    unawarded_count = 0
    for ans in answers:
        mark = next((m for m in db.marks.values() if m.get("answer_id") == ans["id"]), None)
        if not mark or mark.get("final_marks") is None:
            unawarded_count += 1

    is_published = any(p for p in db.publications.values() if p.get("exam_id") == id)

    return {
        "exam_id": id,
        "total_sheets": len(sheets),
        "total_answers": len(answers),
        "unawarded_answers": unawarded_count,
        "is_published": is_published
    }

@router.post("/exams/{id}/publish")
def publish_exam_results(id: str, user: dict = Depends(require_teacher)):
    exam = db.exams.get(id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")

    pub_id = f"p-{uuid.uuid4()}"
    pub_record = {
        "id": pub_id,
        "exam_id": id,
        "published_by": user.get("id", "11111111-1111-1111-1111-111111111111")
    }
    db.publications[pub_id] = pub_record
    return {"message": "Exam results published successfully.", "publication": pub_record}
