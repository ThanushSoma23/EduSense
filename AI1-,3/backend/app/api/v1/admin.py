from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_admin
from app.schemas.schemas import AdminApproveTeacherRequest
from app.db.supabase import db

router = APIRouter()

@router.get("/pending-teachers")
def list_pending_teachers(user: dict = Depends(require_admin)):
    pending = [
        p for p in db.profiles.values()
        if p.get("role") == "teacher" and p.get("status") == "pending"
    ]
    return {"pending_teachers": pending}

@router.post("/approve-teacher")
def approve_or_reject_teacher(
    payload: AdminApproveTeacherRequest,
    user: dict = Depends(require_admin)
):
    teacher = db.profiles.get(payload.teacher_id)
    if not teacher or teacher.get("role") != "teacher":
        raise HTTPException(status_code=404, detail="Teacher profile not found.")

    if payload.action == "approve":
        teacher["status"] = "active"
        msg = f"Teacher account '{teacher.get('full_name')}' approved."
    elif payload.action == "reject":
        teacher["status"] = "rejected"
        msg = f"Teacher registration for '{teacher.get('full_name')}' rejected."
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    return {"message": msg, "teacher": teacher}
