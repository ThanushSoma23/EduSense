from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.models.final_mark import FinalMark
from app.schemas.final_mark import (
    TeacherReviewRequest,
    BatchTeacherReviewRequest,
    FinalMarkResponse,
    StudentQuestionResult,
    StudentExamResultResponse
)
from app.api.deps import get_current_user, get_current_teacher
from app.services.mark_service import review_single_mark_in_tx, execute_batch_review_transactional

router = APIRouter(prefix="/final-marks", tags=["Teacher Review & Final Marks Management"])


@router.post("/review", response_model=FinalMarkResponse, status_code=status.HTTP_200_OK)
def review_and_approve_mark(
    review_in: TeacherReviewRequest,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Teacher review endpoint to approve or modify final marks for a student answer.
    Enforces complete ownership chain: Authenticated Teacher -> Exam -> Question -> Answer.
    Validates mark limits (0 <= marks <= max_marks) and logs audit history.
    """
    final_mark = review_single_mark_in_tx(db=db, review_in=review_in, current_teacher=current_teacher)
    db.commit()
    db.refresh(final_mark)
    return final_mark


@router.post("/batch-review", response_model=List[FinalMarkResponse])
def batch_review_marks(
    batch_in: BatchTeacherReviewRequest,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Allows a teacher to review and approve multiple question final marks in a single atomic transaction.
    If any item fails validation or ownership check, the entire batch is rolled back.
    """
    results = execute_batch_review_transactional(db=db, batch_in=batch_in, current_teacher=current_teacher)
    return results


@router.get("/student/results/{submission_id}", response_model=StudentExamResultResponse)
def get_student_final_results(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves authorized exam results for a student.
    Students can access ONLY their own submission results.
    Prevents student modification of marks.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    # Authorization Check: Student can only view their own submission
    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: You are not authorized to view another student's results."
        )

    # If teacher, verify they own the exam
    if current_user.role == UserRole.TEACHER:
        exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if exam and exam.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted: You are not authorized to view results for another teacher's exam."
            )

    student = db.query(User).filter(User.id == submission.student_id).first()
    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.question_number).all()

    question_results = []
    total_max = 0.0
    total_final = 0.0
    has_final_marks = False

    for q in questions:
        total_max += q.max_marks
        st_ans = db.query(StudentAnswer).filter(
            StudentAnswer.submission_id == submission_id,
            StudentAnswer.question_id == q.id
        ).first()

        extracted_text = st_ans.extracted_text if st_ans else None
        ai_suggested = None
        ai_feedback = None
        final_approved = None
        approval_status = None
        teacher_id = None
        teacher_name = None

        if st_ans:
            eval_rec = db.query(Evaluation).filter(Evaluation.answer_id == st_ans.id).first()
            if eval_rec:
                ai_suggested = eval_rec.suggested_marks
                ai_feedback = eval_rec.feedback

            final_rec = db.query(FinalMark).filter(FinalMark.answer_id == st_ans.id).first()
            if final_rec:
                has_final_marks = True
                final_approved = final_rec.approved_marks
                approval_status = final_rec.approval_status
                teacher_id = final_rec.reviewing_teacher_id
                t_user = db.query(User).filter(User.id == teacher_id).first()
                teacher_name = t_user.name if t_user else None
                total_final += final_approved

        question_results.append(
            StudentQuestionResult(
                question_id=q.id,
                question_number=q.question_number,
                question_text=q.question_text,
                max_marks=q.max_marks,
                extracted_text=extracted_text,
                ai_suggested_marks=ai_suggested,
                ai_feedback=ai_feedback,
                final_approved_marks=final_approved,
                approval_status=approval_status,
                reviewing_teacher_id=teacher_id,
                reviewing_teacher_name=teacher_name
            )
        )

    return StudentExamResultResponse(
        submission_id=submission.id,
        exam_id=exam.id,
        exam_title=exam.title,
        subject=exam.subject,
        student_id=student.id if student else submission.student_id,
        student_name=student.name if student else "Unknown Student",
        submission_time=submission.submission_time,
        processing_status=submission.processing_status,
        total_max_marks=total_max,
        total_final_marks=total_final if has_final_marks else None,
        is_published=submission.processing_status == "REVIEWED",
        questions=question_results
    )
