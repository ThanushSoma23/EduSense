from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.schemas.submission import (
    AnswerSheetCreate, AnswerSheetUpdate, AnswerSheetResponse,
    StudentAnswerCreate, StudentAnswerResponse
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/submissions", tags=["Answer-Sheet Submissions"])


@router.post("", response_model=AnswerSheetResponse, status_code=status.HTTP_201_CREATED)
def create_submission(
    sub_in: AnswerSheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits an answer sheet record for an exam.
    Students submit for themselves; Teachers may submit on behalf of a student.
    """
    # Verify exam exists
    exam = db.query(Exam).filter(Exam.id == sub_in.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    student_id = current_user.id
    if current_user.role == UserRole.TEACHER:
        if not sub_in.student_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teachers must specify student_id when creating a submission."
            )
        student_id = sub_in.student_id

    # Check for duplicate submission
    existing = db.query(AnswerSheet).filter(
        AnswerSheet.student_id == student_id,
        AnswerSheet.exam_id == sub_in.exam_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A submission for this exam already exists for the specified student."
        )

    submission = AnswerSheet(
        student_id=student_id,
        exam_id=sub_in.exam_id,
        file_reference=sub_in.file_reference,
        processing_status="PENDING"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("", response_model=List[AnswerSheetResponse])
def list_submissions(
    exam_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists submissions.
    Students can only view their own submissions.
    Teachers can view submissions for exams they teach (or filter by exam_id).
    """
    query = db.query(AnswerSheet)
    if current_user.role == UserRole.STUDENT:
        query = query.filter(AnswerSheet.student_id == current_user.id)
    elif current_user.role == UserRole.TEACHER:
        # Filter exams created by teacher
        teacher_exam_ids = [e.id for e in db.query(Exam.id).filter(Exam.teacher_id == current_user.id).all()]
        query = query.filter(AnswerSheet.exam_id.in_(teacher_exam_ids))

    if exam_id:
        query = query.filter(AnswerSheet.exam_id == exam_id)

    return query.all()


@router.get("/{submission_id}", response_model=AnswerSheetResponse)
def get_submission_detail(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves submission details including question answers.
    Enforces authorization: students can only access their own submissions.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if current_user.role == UserRole.TEACHER:
        exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if exam and exam.teacher_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return submission


@router.post("/{submission_id}/answers", response_model=StudentAnswerResponse, status_code=status.HTTP_201_CREATED)
def create_student_answer(
    submission_id: int,
    ans_in: StudentAnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stores extracted text for a specific question (used by OCR pipeline).
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    # Verify question belongs to the exam
    question = db.query(Question).filter(
        Question.id == ans_in.question_id,
        Question.exam_id == submission.exam_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question ID does not belong to the exam associated with this submission."
        )

    # Check duplicate student_answer
    existing = db.query(StudentAnswer).filter(
        StudentAnswer.submission_id == submission_id,
        StudentAnswer.question_id == ans_in.question_id
    ).first()

    if existing:
        # Update existing answer text if present
        existing.extracted_text = ans_in.extracted_text
        existing.ocr_confidence = ans_in.ocr_confidence
        existing.extraction_status = ans_in.extraction_status or "SUCCESS"
        db.commit()
        db.refresh(existing)
        return existing

    student_answer = StudentAnswer(
        submission_id=submission_id,
        question_id=ans_in.question_id,
        extracted_text=ans_in.extracted_text,
        ocr_confidence=ans_in.ocr_confidence,
        extraction_status=ans_in.extraction_status or "SUCCESS"
    )
    db.add(student_answer)

    # Update processing status of answer sheet to EXTRACTED if pending
    if submission.processing_status == "PENDING":
        submission.processing_status = "EXTRACTED"

    db.commit()
    db.refresh(student_answer)
    return student_answer
