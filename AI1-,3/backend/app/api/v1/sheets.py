import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from typing import Dict, Any, List
from PIL import Image
from app.core.security import require_teacher
from app.core.rate_limiter import auth_rate_limiter
from app.db.supabase import db
from app.preprocessing.pipeline import preprocess_sheet
from app.agents.tools import tool_update_sheet_status

logger = logging.getLogger(__name__)

# Enforce Image Decompression Bomb protection
Image.MAX_IMAGE_PIXELS = 50_000_000

router = APIRouter(prefix="/sheets", tags=["Answer Sheet Ingestion"])

ALLOWED_SHEET_MAGIC = [
    b"%PDF", # PDF
    b"\xff\xd8\xff", # JPG/JPEG
    b"\x89PNG\r\n\x1a\n", # PNG
]

@router.post("/upload")
async def upload_answer_sheet(
    request: Request,
    file: UploadFile = File(...),
    exam_id: str = "e1111111-1111-1111-1111-111111111111",
    student_id: str = "22222222-2222-2222-2222-222222222222",
    current_user: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    """
    Minimal upload endpoint for scanned answer sheets (Teacher-only).
    Magic-byte check, size cap (25MB), Image.MAX_IMAGE_PIXELS guard, ignores client filename.
    Stores file and executes preprocess_sheet pipeline.
    """
    auth_rate_limiter.check_rate_limit(request)

    contents = await file.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 25MB limit.")

    # Magic byte verification
    is_valid_magic = any(contents.startswith(m) for m in ALLOWED_SHEET_MAGIC)
    if not is_valid_magic:
        raise HTTPException(status_code=400, detail="Invalid image or PDF format. Acceptable formats: PDF, JPG, PNG.")

    sheet_id = f"sheet-{uuid.uuid4()}"
    institution_id = current_user.get("college_id", "c1111111-1111-1111-1111-111111111111")

    # Record sheet in DB
    sheet_record = {
        "id": sheet_id,
        "exam_id": exam_id,
        "student_id": student_id,
        "file_url": f"local://storage/sheets/{sheet_id}.bin",
        "status": "UPLOADED",
        "failed_stage": None
    }
    db.answer_sheets[sheet_id] = sheet_record

    try:
        tool_update_sheet_status(sheet_id, "PREPROCESSED")
        pages = preprocess_sheet(
            input_sources=[contents],
            institution_id=institution_id,
            exam_id=exam_id,
            sheet_id=sheet_id
        )
        sheet_record["status"] = "PREPROCESSED"
        sheet_record["pages_count"] = len(pages)
        return {
            "message": "Answer sheet uploaded and preprocessed successfully.",
            "sheet_id": sheet_id,
            "status": "PREPROCESSED",
            "pages": [
                {
                    "page_number": p.page_number,
                    "clean_path": p.clean_path,
                    "quality_score": p.quality_score,
                    "flags": p.flags
                }
                for p in pages
            ]
        }
    except Exception as e:
        logger.error(f"Preprocessing failed for sheet {sheet_id}: {e}")
        tool_update_sheet_status(sheet_id, "FAILED", error=str(e), failed_stage="PREPROCESSED")
        raise HTTPException(status_code=500, detail=f"Preprocessing failed: {e}")
