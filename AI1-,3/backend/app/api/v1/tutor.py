import uuid
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.core.security import get_current_user, require_student
from app.core.rate_limiter import auth_rate_limiter
from app.evaluation.rag_kb import hybrid_retrieve
from app.db.supabase import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])

class TutorChatRequest(BaseModel):
    exam_id: str
    question_id: str
    message: str

@router.post("/chat")
def tutor_chat(
    req: TutorChatRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_student)
) -> Dict[str, Any]:
    """
    AI Tutor endpoint for students.
    Available ONLY for PUBLISHED results belonging to the authenticated student.
    Uses KB retrieval with exact cited excerpts [source, page]. Refuses fabricated citations.
    """
    auth_rate_limiter.check_rate_limit(request)
    student_id = current_user["id"]

    # 0. Prompt Injection Check on Student Tutor Input
    from app.evaluation.evaluator import detect_prompt_injection
    if detect_prompt_injection(req.message):
        return {
            "reply": "Security Alert: Prompt injection attempt detected. AI Tutor instructions cannot be overridden, and scores cannot be modified via chat.",
            "citations": [],
            "flags": ["prompt_injection_suspected"]
        }

    # 1. Verify Exam Publication Status

    publication = next((p for p in db.publications.values() if p.get("exam_id") == req.exam_id), None)
    if not publication:
        raise HTTPException(
            status_code=403,
            detail="Tutor access denied: Exam results have not been published by the teacher yet."
        )

    # 2. Verify Student Sheet Ownership
    student_sheet = next(
        (s for s in db.answer_sheets.values() if s.get("exam_id") == req.exam_id and s.get("student_id") == student_id),
        None
    )
    if not student_sheet:
        raise HTTPException(status_code=403, detail="Tutor access denied: No answer sheet found for this student.")

    # 3. Retrieve Question & Published Results Context
    question = db.questions.get(req.question_id, {})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    answer_record = next(
        (a for a in db.answers.values() if a.get("sheet_id") == student_sheet["id"] and a.get("question_id") == req.question_id),
        None
    )

    # Published teacher score (read via published-results view helper, NEVER via agent tools)
    mark_record = None
    if answer_record:
        published_scores = getattr(db, "published_results", {})
        mark_record = published_scores.get(answer_record["id"])



    # 4. KB Retrieval for "Teach me" queries
    institution_id = current_user.get("college_id", "c1111111-1111-1111-1111-111111111111")
    kb_chunks = hybrid_retrieve(
        query=req.message,
        subject_id=question.get("subject", "Computer Science"),
        institution_id=institution_id,
        k=2
    )

    # 5. Synthesize Tutor Response with Citations
    citations = []
    if kb_chunks:
        citations = [
            {"source": c["source"], "page": c["page"], "excerpt": c["chunk_text"][:100]}
            for c in kb_chunks
        ]
        tutor_response = f"Based on your course materials:\n{kb_chunks[0]['chunk_text'][:250]}...\nCitations: [{kb_chunks[0]['source']}, Page {kb_chunks[0]['page']}]."
    else:
        tutor_response = "I searched your official course knowledge base, but no matching reference passages were found for this topic. I cannot provide a citation without verified reference text."

    if mark_record and "mark" in req.message.lower():
        awarded = mark_record.get("awarded_score") or mark_record.get("score")
        remarks = mark_record.get("remarks") or "No remarks provided."
        tutor_response += f"\n\nRegarding your score: Teacher awarded {awarded} marks. Remarks: '{remarks}'."


    # 6. Persist turns in tutor_messages table
    msg_id = f"tutor-{uuid.uuid4()}"
    tutor_turn = {
        "id": msg_id,
        "student_id": student_id,
        "exam_id": req.exam_id,
        "question_id": req.question_id,
        "role": "assistant",
        "content": tutor_response,
        "citations": citations
    }
    if not hasattr(db, "tutor_messages"):
        db.tutor_messages = {}
    db.tutor_messages[msg_id] = tutor_turn

    return {
        "reply": tutor_response,
        "citations": citations,
        "published": True
    }
