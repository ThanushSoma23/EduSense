from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import StudentAnswer
from app.models.final_mark import FinalMark
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse
)
from app.api.deps import get_current_user, get_current_teacher

router = APIRouter(prefix="/exams", tags=["Examination Management"])


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_in: ExamCreate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Creates a new examination with optional questions. Restrictive to authorized Teachers.
    """
    exam = Exam(
        title=exam_in.title,
        subject=exam_in.subject,
        teacher_id=current_teacher.id,
        status="DRAFT"
    )
    db.add(exam)
    db.flush()

    if exam_in.questions:
        q_numbers = set()
        for q_in in exam_in.questions:
            if q_in.question_number in q_numbers:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate question number {q_in.question_number} in request."
                )
            q_numbers.add(q_in.question_number)
            question = Question(
                exam_id=exam.id,
                question_number=q_in.question_number,
                question_text=q_in.question_text,
                model_answer=q_in.model_answer,
                max_marks=q_in.max_marks,
                rubric=q_in.rubric
            )
            db.add(question)

    db.commit()
    db.refresh(exam)
    return exam


@router.get("", response_model=List[ExamResponse])
def list_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists exams accessible to the authenticated user.
    Teachers see exams they created. Students see published exams.
    """
    if current_user.role == UserRole.TEACHER:
        exams = db.query(Exam).filter(Exam.teacher_id == current_user.id).all()
    else:
        exams = db.query(Exam).filter(Exam.status.in_(["PUBLISHED", "COMPLETED"])).all()
    return exams


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam_detail(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves an exam by ID along with its questions.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found"
        )
    if current_user.role == UserRole.TEACHER and exam.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this exam."
        )
    return exam


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Updates exam details or status (Teacher only).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this exam.")

    if exam_in.title is not None:
        exam.title = exam_in.title
    if exam_in.subject is not None:
        exam.subject = exam_in.subject
    if exam_in.status is not None:
        exam.status = exam_in.status

    db.commit()
    db.refresh(exam)
    return exam


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Deletes an exam and associated questions (Teacher only).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this exam.")

    db.delete(exam)
    db.commit()
    return None


@router.post("/{exam_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def add_question_to_exam(
    exam_id: int,
    q_in: QuestionCreate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Adds a new question to an exam.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this exam.")

    existing_q = db.query(Question).filter(
        Question.exam_id == exam_id,
        Question.question_number == q_in.question_number
    ).first()
    if existing_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question number {q_in.question_number} already exists for this exam."
        )

    question = Question(
        exam_id=exam_id,
        question_number=q_in.question_number,
        question_text=q_in.question_text,
        model_answer=q_in.model_answer,
        max_marks=q_in.max_marks,
        rubric=q_in.rubric
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.put("/{exam_id}/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    exam_id: int,
    question_id: int,
    q_in: QuestionUpdate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Updates a question inside an exam.
    Prevents reducing max_marks below already approved student final marks.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    question = db.query(Question).filter(Question.id == question_id, Question.exam_id == exam_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if q_in.max_marks is not None and q_in.max_marks < question.max_marks:
        # Check if existing approved final marks exceed new max_marks
        highest_approved = (
            db.query(func.max(FinalMark.approved_marks))
            .join(StudentAnswer, StudentAnswer.id == FinalMark.answer_id)
            .filter(StudentAnswer.question_id == question_id)
            .scalar()
        )
        if highest_approved is not None and highest_approved > q_in.max_marks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce max_marks to {q_in.max_marks}: existing approved student final mark ({highest_approved}) exceeds the new limit."
            )

    if q_in.question_number is not None:
        question.question_number = q_in.question_number
    if q_in.question_text is not None:
        question.question_text = q_in.question_text
    if q_in.model_answer is not None:
        question.model_answer = q_in.model_answer
    if q_in.max_marks is not None:
        question.max_marks = q_in.max_marks
    if q_in.rubric is not None:
        question.rubric = q_in.rubric

    db.commit()
    db.refresh(question)
    return question
