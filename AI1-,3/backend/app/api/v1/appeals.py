import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_student, require_teacher
from app.schemas.schemas import AppealCreate
from app.db.supabase import db

router = APIRouter()

@router.post("/appeals")
def create_appeal(payload: AppealCreate, user: dict = Depends(require_student)):
    appeal_id = f"app-{uuid.uuid4()}"
    student_id = user.get("id", "22222222-2222-2222-2222-222222222222")

    ai_summary = f"Student requests re-evaluation for answer {payload.answer_id}. Reason: {payload.student_reason}"

    appeal_record = {
        "id": appeal_id,
        "answer_id": payload.answer_id,
        "student_id": student_id,
        "student_reason": payload.student_reason,
        "ai_summary": ai_summary,
        "status": "pending"
    }
    db.appeals[appeal_id] = appeal_record
    return {"message": "Appeal submitted successfully", "appeal": appeal_record}

@router.get("/appeals")
def list_appeals(user: dict = Depends(require_teacher)):
    return {"appeals": list(db.appeals.values())}
