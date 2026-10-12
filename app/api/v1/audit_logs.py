from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse
from app.api.deps import get_current_teacher

router = APIRouter(prefix="/audit-logs", tags=["Audit & Integrity Logs"])


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    final_mark_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Retrieves audit logs of final mark modifications. Restrictive to authorized Teachers.
    """
    query = db.query(AuditLog, User.name.label("teacher_name")).join(
        User, AuditLog.teacher_id == User.id
    )

    if final_mark_id:
        query = query.filter(AuditLog.final_mark_id == final_mark_id)
    if teacher_id:
        query = query.filter(AuditLog.teacher_id == teacher_id)

    records = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    output = []
    for log_item, t_name in records:
        log_res = AuditLogResponse(
            id=log_item.id,
            final_mark_id=log_item.final_mark_id,
            teacher_id=log_item.teacher_id,
            teacher_name=t_name,
            action=log_item.action,
            previous_value=log_item.previous_value,
            updated_value=log_item.updated_value,
            reason=log_item.reason,
            timestamp=log_item.timestamp
        )
        output.append(log_res)

    return output
