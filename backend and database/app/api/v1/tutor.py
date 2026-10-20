import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.models.final_mark import FinalMark
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["AI Personal Tutor"])


class CitationItem(BaseModel):
    source: str
    page: Optional[int | str] = None
    excerpt: str


class TutorChatRequest(BaseModel):
    exam_id: Any
    question_id: Any
    message: str
    submission_id: Optional[Any] = None


class TutorChatResponse(BaseModel):
    reply: str
    citations: List[CitationItem] = []
    published: bool = True
    provider: str


def detect_prompt_injection(message: str) -> bool:
    """
    Detects attempts by students to alter grading prompts, overwrite instructions,
    or manipulate scores via tutor chat.
    """
    suspicious_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?prior\s+instructions",
        r"override\s+(the\s+)?system",
        r"system\s+prompt",
        r"you\s+are\s+now\s+(an?\s+)?admin",
        r"pretend\s+you\s+are",
        r"give\s+me\s+full\s+marks",
        r"change\s+my\s+mark",
        r"update\s+my\s+score",
        r"override\s+my\s+grade",
        r"jailbreak",
        r"bypass\s+rubric"
    ]
    msg_lower = message.lower()
    for pat in suspicious_patterns:
        if re.search(pat, msg_lower):
            return True
    return False


def call_gemini_tutor(
    user_message: str,
    subject: str,
    exam_title: str,
    question_num: int,
    question_text: str,
    model_answer: str,
    rubric: Optional[str],
    student_extracted: Optional[str],
    score_summary: str,
    feedback: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """
    Calls Gemini using google.genai Client with model fallbacks.
    Returns (reply_text, provider_name) or (None, None).
    """
    if not settings.GEMINI_API_KEY:
        return None, None

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]

    system_instruction = (
        "You are EduSense AI Tutor, a friendly, encouraging, and pedagogically rigorous academic tutor. "
        "You are helping a student understand their published exam evaluation. "
        "RULES:\n"
        "1. Explain concepts clearly, constructively, and step-by-step.\n"
        "2. You CANNOT change, promise to change, or alter the student's marks. Teacher-approved marks are final.\n"
        "3. Base your academic explanations on the Question, Model Answer, Rubric, and the Student's Answer.\n"
        "4. Keep explanations concise (150-250 words) unless the student asks for an in-depth breakdown."
    )

    prompt = (
        f"{system_instruction}\n\n"
        f"--- CONTEXT ---\n"
        f"Subject: {subject}\n"
        f"Exam: {exam_title}\n"
        f"Question #{question_num}: {question_text}\n"
        f"Model Answer: {model_answer}\n"
        f"Rubric / Key Concepts: {rubric or 'Standard conceptual completeness'}\n"
        f"Student's Answer on Paper: {student_extracted or 'Not provided'}\n"
        f"Awarded Score: {score_summary}\n"
        f"Teacher / AI Feedback: {feedback or 'None'}\n\n"
        f"--- STUDENT'S QUESTION ---\n"
        f"{user_message}\n\n"
        f"--- YOUR TUTOR RESPONSE ---"
    )

    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    return response.text.strip(), model_name
            except Exception as e:
                logger.warning(f"Gemini model {model_name} invocation failed: {e}. Trying fallback model...")
                continue
    except Exception as e:
        logger.error(f"Error initializing Google GenAI client: {e}")

    return None, None


@router.post("/chat", response_model=TutorChatResponse)
def tutor_chat(
    req: TutorChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    AI Tutor endpoint for students.
    Enforces:
    1. Prompt injection defense.
    2. Published-only gating (exam.status == 'PUBLISHED').
    3. Student answer sheet ownership check.
    4. Google Gemini synthesis with transparent fallback labeling.
    """
    # 1. Prompt Injection Defense
    if detect_prompt_injection(req.message):
        return TutorChatResponse(
            reply="Security Alert: Prompt injection attempt detected. AI Tutor instructions cannot be overridden, and scores cannot be modified via chat.",
            citations=[],
            published=True,
            provider="security_guard"
        )

    # 2. Verify Exam Publication Status
    try:
        e_id_int = int(req.exam_id)
        exam = db.query(Exam).filter(Exam.id == e_id_int).first()
    except (ValueError, TypeError):
        exam = db.query(Exam).filter(Exam.title.ilike(f"%{req.exam_id}%")).first()

    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam '{req.exam_id}' not found."
        )

    if exam.status != "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tutor access denied: Exam results have not been published by the teacher yet."
        )

    # 3. Verify Student Sheet Ownership
    submission = None
    if current_user.role == UserRole.STUDENT:
        # Check by student_id & exam_id
        submission = db.query(AnswerSheet).filter(
            AnswerSheet.exam_id == exam.id,
            AnswerSheet.student_id == current_user.id
        ).first()

        # Or check if submission_id was explicitly provided and belongs to user
        if not submission and req.submission_id:
            try:
                sub_id_int = int(req.submission_id)
                submission = db.query(AnswerSheet).filter(
                    AnswerSheet.id == sub_id_int,
                    AnswerSheet.student_id == current_user.id
                ).first()
            except (ValueError, TypeError):
                pass

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tutor access denied: No answer sheet found for this student for this exam."
            )
    else:
        # Teachers / Admins testing the tutor
        if req.submission_id:
            try:
                sub_id_int = int(req.submission_id)
                submission = db.query(AnswerSheet).filter(AnswerSheet.id == sub_id_int).first()
            except (ValueError, TypeError):
                pass
        if not submission:
            submission = db.query(AnswerSheet).filter(AnswerSheet.exam_id == exam.id).first()

    # 4. Question & Student Answer Retrieval
    question = None
    try:
        q_id_int = int(req.question_id)
        # Search by database Question ID
        question = db.query(Question).filter(Question.id == q_id_int, Question.exam_id == exam.id).first()
        # Fallback to search by Question Number (1, 2, 3...) within this exam
        if not question:
            question = db.query(Question).filter(Question.question_number == q_id_int, Question.exam_id == exam.id).first()
    except (ValueError, TypeError):
        pass

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question #{req.question_id} was not found for exam '{exam.title}'. Please select a valid question."
        )

    logger.info(
        f"[TUTOR_CHAT] Exam ID: {exam.id} ('{exam.title}'), "
        f"Req Question ID: {req.question_id}, "
        f"Resolved Question: Q{question.question_number} (ID {question.id}), "
        f"Student ID: {current_user.id}, "
        f"Question Prompt: '{question.question_text[:60]}...'"
    )

    student_answer = None
    final_mark = None
    evaluation = None
    if submission:
        student_answer = db.query(StudentAnswer).filter(
            StudentAnswer.submission_id == submission.id,
            StudentAnswer.question_id == question.id
        ).first()
        if student_answer:
            final_mark = db.query(FinalMark).filter(FinalMark.answer_id == student_answer.id).first()
            evaluation = db.query(Evaluation).filter(Evaluation.answer_id == student_answer.id).first()

    # 5. Score summary & Citations
    if final_mark:
        score_summary = f"{final_mark.approved_marks} / {question.max_marks} (Approved by Teacher)"
    elif evaluation:
        score_summary = f"{evaluation.suggested_marks} / {question.max_marks} (Suggested Marks)"
    else:
        score_summary = f"Max marks: {question.max_marks}"

    # Clean rubric parsing to avoid displaying empty array '[]'
    rubric_text = None
    if question.rubric:
        try:
            parsed = json.loads(question.rubric)
            if isinstance(parsed, list):
                if len(parsed) > 0:
                    rubric_text = ", ".join(str(x) for x in parsed)
            elif isinstance(parsed, str) and parsed.strip() and parsed.strip() != "[]":
                rubric_text = parsed.strip()
        except Exception:
            clean = question.rubric.strip()
            if clean and clean != "[]":
                rubric_text = clean

    rubric_display = rubric_text if rubric_text else "Not specified by instructor for this question (evaluated against official model answer)."

    feedback_text = (
        evaluation.feedback
        if evaluation and evaluation.feedback
        else "Evaluated against official model answer and standard conceptual completeness."
    )

    model_ans_text = question.model_answer or ""
    model_ans_excerpt = (
        model_ans_text[:140] + ("..." if len(model_ans_text) > 140 else "")
        if model_ans_text
        else "Official model solution not specified by instructor."
    )

    citations = [
        CitationItem(
            source=f"{exam.title} - Question {question.question_number}",
            page=question.question_number,
            excerpt=model_ans_excerpt
        )
    ]

    # 6. Call Gemini or Fallback
    llm_reply, provider = call_gemini_tutor(
        user_message=req.message,
        subject=exam.subject,
        exam_title=exam.title,
        question_num=question.question_number,
        question_text=question.question_text,
        model_answer=model_ans_text,
        rubric=rubric_display,
        student_extracted=student_answer.extracted_text if student_answer else None,
        score_summary=score_summary,
        feedback=feedback_text
    )

    if llm_reply and provider:
        return TutorChatResponse(
            reply=llm_reply,
            citations=citations,
            published=True,
            provider=provider
        )

    # Fallback synthesizer strictly grounded in the requested question
    model_ans_overview = (
        f'"{model_ans_text[:220]}{"..." if len(model_ans_text) > 220 else ""}"'
        if model_ans_text
        else "Official model solution has not been provided by the instructor for this question."
    )

    fallback_reply = (
        f"Regarding Question {question.question_number} ({exam.subject}):\n\n"
        f"• Reference Solution Overview:\n{model_ans_overview}\n\n"
        f"• Rubric Criteria: {rubric_display}\n\n"
        f"• Evaluator Assessment: {feedback_text}\n\n"
        f"• Your Awarded Score: {score_summary}\n\n"
        f"• Study Tip: In response to '{req.message}', compare your steps to the model solution above. "
        f"Ensure key technical distinctions and steps required by the prompt are explicitly addressed."
    )

    return TutorChatResponse(
        reply=fallback_reply,
        citations=citations,
        published=True,
        provider="local_fallback (offline pedagogical model)"
    )


@router.get("/context/{exam_id}")
def get_tutor_context(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns exam status, publication gating check, and questions list for tutor UI.
    """
    try:
        e_int = int(exam_id)
        exam = db.query(Exam).filter(Exam.id == e_int).first()
    except (ValueError, TypeError):
        exam = db.query(Exam).filter(Exam.title.ilike(f"%{exam_id}%")).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    is_published = (exam.status == "PUBLISHED")
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.question_number).all()

    return {
        "exam_id": exam.id,
        "exam_title": exam.title,
        "subject": exam.subject,
        "is_published": is_published,
        "questions": [
            {
                "id": q.id,
                "question_number": q.question_number,
                "question_text": q.question_text,
                "max_marks": q.max_marks,
                "model_answer": q.model_answer,
                "rubric": q.rubric
            }
            for q in questions
        ]
    }
