import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Query
from pydantic import BaseModel
from app.core.security import require_teacher, require_active_user
from app.core.rate_limiter import auth_rate_limiter
from app.core.config import settings
from app.db.supabase import db
from app.services.ocr import run_ocr
from app.services.segmentation import segment_transcript
from app.agents.tools import tool_update_sheet_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["AIML-2 Handwritten OCR & Segmentation"])

class SegmentOnlyRequest(BaseModel):
    lines: List[Dict[str, Any]]
    threshold: Optional[float] = None

class AnswerSegmentResponse(BaseModel):
    question_number: int
    text: str
    ocr_confidence: float
    needs_review: bool

class TranscribeResponse(BaseModel):
    sheet_id: Optional[str] = None
    backend_used: str
    total_lines: int
    total_questions: int
    answers: List[AnswerSegmentResponse]
    overall_confidence: float
    needs_review: bool
    raw_lines: Optional[List[Dict[str, Any]]] = None

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_image(
    request: Request,
    file: UploadFile = File(...),
    backend: Optional[str] = Query(default=None, description="OCR backend: trocr, easyocr, or mock"),
    include_raw_lines: bool = Query(default=False, description="Include raw per-line OCR tokens"),
    current_user: Dict[str, Any] = Depends(require_active_user)
) -> TranscribeResponse:
    """
    AIML-2 Core Endpoint:
    Accepts an answer sheet image (JPEG, PNG), performs handwriting OCR via TrOCR / EasyOCR / Mock,
    segments transcript into per-question answers, and assigns confidence and review flags.
    """
    auth_rate_limiter.check_rate_limit(request)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    chosen_backend = backend or settings.OCR_BACKEND
    ocr_lines = run_ocr(contents, backend_override=chosen_backend)
    segmented = segment_transcript(ocr_lines)

    all_confs = [s["ocr_confidence"] for s in segmented] if segmented else [1.0]
    overall_conf = round(sum(all_confs) / len(all_confs), 4) if all_confs else 1.0
    any_needs_review = any(s["needs_review"] for s in segmented)

    return TranscribeResponse(
        sheet_id=None,
        backend_used=chosen_backend,
        total_lines=len(ocr_lines),
        total_questions=len(segmented),
        answers=[
            AnswerSegmentResponse(
                question_number=s["question_number"],
                text=s["text"],
                ocr_confidence=s["ocr_confidence"],
                needs_review=s["needs_review"]
            )
            for s in segmented
        ],
        overall_confidence=overall_conf,
        needs_review=any_needs_review,
        raw_lines=ocr_lines if include_raw_lines else None
    )

@router.post("/sheets/{sheet_id}/transcribe", response_model=TranscribeResponse)
def transcribe_answer_sheet(
    sheet_id: str,
    backend: Optional[str] = Query(default=None),
    current_user: Dict[str, Any] = Depends(require_teacher)
) -> TranscribeResponse:
    """
    Process an ingested answer sheet record:
    1. Runs OCR and Segmentation.
    2. Upserts answer records in db.answers so AIML-3 can immediately evaluate them.
    3. Updates answer sheet status to 'OCR_COMPLETE' and 'SEGMENTED'.
    """
    sheet = db.answer_sheets.get(sheet_id)
    if not sheet:
        raise HTTPException(status_code=404, detail="Answer sheet not found.")

    chosen_backend = backend or settings.OCR_BACKEND

    # Fetch preprocessed clean image or mock bytes
    tool_update_sheet_status(sheet_id, "OCR_COMPLETE")
    ocr_lines = run_ocr(b"", backend_override=chosen_backend)

    tool_update_sheet_status(sheet_id, "SEGMENTED")
    segmented = segment_transcript(ocr_lines)

    exam_id = sheet.get("exam_id", "e1111111-1111-1111-1111-111111111111")
    exam_questions = [q for q in db.questions.values() if q.get("exam_id") == exam_id]

    # Save answers to db.answers
    for s in segmented:
        q_match = next((q for q in exam_questions if q.get("number") == s["question_number"]), None)
        q_id = q_match["id"] if q_match else f"q-{s['question_number']}"

        # Find existing answer record or create new
        existing_ans = next(
            (a for a in db.answers.values() if a.get("sheet_id") == sheet_id and a.get("question_id") == q_id),
            None
        )
        if existing_ans:
            existing_ans["text"] = s["text"]
            existing_ans["ocr_confidence"] = s["ocr_confidence"]
            existing_ans["needs_review"] = s["needs_review"]
        else:
            ans_id = f"ans-{uuid.uuid4()}"
            db.answers[ans_id] = {
                "id": ans_id,
                "sheet_id": sheet_id,
                "question_id": q_id,
                "text": s["text"],
                "ocr_confidence": s["ocr_confidence"],
                "needs_review": s["needs_review"]
            }

    all_confs = [s["ocr_confidence"] for s in segmented] if segmented else [1.0]
    overall_conf = round(sum(all_confs) / len(all_confs), 4) if all_confs else 1.0
    any_needs_review = any(s["needs_review"] for s in segmented)

    return TranscribeResponse(
        sheet_id=sheet_id,
        backend_used=chosen_backend,
        total_lines=len(ocr_lines),
        total_questions=len(segmented),
        answers=[
            AnswerSegmentResponse(
                question_number=s["question_number"],
                text=s["text"],
                ocr_confidence=s["ocr_confidence"],
                needs_review=s["needs_review"]
            )
            for s in segmented
        ],
        overall_confidence=overall_conf,
        needs_review=any_needs_review
    )

@router.post("/segment")
def segment_raw_lines(payload: SegmentOnlyRequest) -> Dict[str, Any]:
    """Segment an array of OCR line dictionaries directly."""
    segmented = segment_transcript(payload.lines, review_threshold=payload.threshold)
    return {
        "total_questions": len(segmented),
        "answers": segmented
    }
