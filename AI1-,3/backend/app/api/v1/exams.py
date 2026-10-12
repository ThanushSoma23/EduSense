import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from app.core.security import require_teacher
from app.schemas.schemas import ExamCreate
from app.db.supabase import db

router = APIRouter()

@router.get("")
def list_exams(user: dict = Depends(require_teacher)):
    teacher_id = user.get("id", "11111111-1111-1111-1111-111111111111")
    exams = [e for e in db.exams.values() if e.get("teacher_id") == teacher_id]
    return {"exams": exams}

@router.post("")
def create_exam(exam_in: ExamCreate, user: dict = Depends(require_teacher)):
    exam_id = f"e-{uuid.uuid4()}"
    teacher_id = user.get("id", "11111111-1111-1111-1111-111111111111")

    exam_record = {
        "id": exam_id,
        "title": exam_in.title,
        "subject": exam_in.subject,
        "code": exam_in.code,
        "teacher_id": teacher_id
    }
    db.exams[exam_id] = exam_record

    for q in exam_in.questions:
        q_id = f"q-{uuid.uuid4()}"
        q_record = {
            "id": q_id,
            "exam_id": exam_id,
            "number": q.number,
            "text": q.text,
            "max_marks": q.max_marks,
            "model_answer": q.model_answer,
            "concepts": q.concepts
        }
        db.questions[q_id] = q_record

    return {"message": "Exam created successfully", "exam": exam_record}

@router.get("/{id}")
def get_exam_details(id: str, user: dict = Depends(require_teacher)):
    exam = db.exams.get(id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")
    questions = [q for q in db.questions.values() if q.get("exam_id") == id]
    return {"exam": exam, "questions": questions}

@router.post("/{id}/reference")
async def upload_reference_material(
    id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_teacher)
):
    source_id = f"src-{uuid.uuid4()}"
    source_record = {
        "id": source_id,
        "exam_id": id,
        "title": file.filename or "Reference Document"
    }
    db.kb_sources[source_id] = source_record

    # Mock chunking and embedding
    chunk_id = f"chk-{uuid.uuid4()}"
    db.kb_chunks[chunk_id] = {
        "id": chunk_id,
        "source_id": source_id,
        "page": 1,
        "text": f"Reference content extracted from {file.filename}."
    }

    return {"message": "Reference material processed and indexed.", "source": source_record}
