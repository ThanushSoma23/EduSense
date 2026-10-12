from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    final_mark_id: Optional[int] = None
    teacher_id: int
    teacher_name: Optional[str] = None
    action: str
    previous_value: Optional[str] = None
    updated_value: str
    reason: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
