import json
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_final_mark_action(
    db: Session,
    teacher_id: int,
    action: str,
    final_mark_id: Optional[int],
    previous_value: Optional[Any],
    updated_value: Any,
    reason: Optional[str] = None
) -> AuditLog:
    """
    Creates an audit record when a teacher creates, updates, approves, or modifies final marks.
    Executed inside the active database transaction to ensure atomicity.
    """
    prev_str = json.dumps(previous_value) if isinstance(previous_value, (dict, list)) else (str(previous_value) if previous_value is not None else None)
    upd_str = json.dumps(updated_value) if isinstance(updated_value, (dict, list)) else str(updated_value)

    log_entry = AuditLog(
        final_mark_id=final_mark_id,
        teacher_id=teacher_id,
        action=action,
        previous_value=prev_str,
        updated_value=upd_str,
        reason=reason,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.flush()
    return log_entry
