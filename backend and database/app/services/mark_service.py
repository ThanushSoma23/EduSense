from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.final_mark import FinalMark
from app.schemas.final_mark import TeacherReviewRequest, BatchTeacherReviewRequest
from app.services.audit_service import log_final_mark_action


def review_single_mark_in_tx(
    db: Session,
    review_in: TeacherReviewRequest,
    current_teacher: User
) -> FinalMark:
    """
    Core business logic for approving or modifying a student answer mark.
    Strictly verifies complete ownership chain:
    Authenticated Teacher -> Exam -> Question -> Student Answer.
    Executed inside the active database transaction.
    """
    # 1. Fetch StudentAnswer with pessimism locking
    answer = (
        db.query(StudentAnswer)
        .filter(StudentAnswer.id == review_in.answer_id)
        .with_for_update()
        .first()
    )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student answer #{review_in.answer_id} not found."
        )

    # 2. Fetch Question
    question = db.query(Question).filter(Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question associated with answer #{review_in.answer_id} not found."
        )

    # 3. Fetch Exam and verify Teacher Ownership
    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam associated with answer #{review_in.answer_id} not found."
        )

    if exam.teacher_id != current_teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Exam #{exam.id} was created by another teacher."
        )

    # 4. Cross-exam relationship integrity check (Submission exam matches Question exam)
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == answer.submission_id).first()
    if not submission or submission.exam_id != exam.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data integrity error: Answer #{answer.id} belongs to a question from a different exam."
        )

    # 5. Validate approved marks bounds: 0 <= approved_marks <= max_marks
    if review_in.approved_marks < 0.0 or review_in.approved_marks > question.max_marks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approved marks ({review_in.approved_marks}) must be between 0.0 and maximum marks ({question.max_marks}) for Question #{question.question_number}."
        )

    # 6. Create or Update FinalMark
    existing_mark = (
        db.query(FinalMark)
        .filter(FinalMark.answer_id == review_in.answer_id)
        .with_for_update()
        .first()
    )

    if existing_mark:
        prev_data = {
            "approved_marks": existing_mark.approved_marks,
            "approval_status": existing_mark.approval_status,
            "reviewing_teacher_id": existing_mark.reviewing_teacher_id
        }
        
        existing_mark.approved_marks = review_in.approved_marks
        existing_mark.approval_status = review_in.approval_status
        existing_mark.reviewing_teacher_id = current_teacher.id
        existing_mark.approval_timestamp = datetime.now(timezone.utc)

        updated_data = {
            "approved_marks": existing_mark.approved_marks,
            "approval_status": existing_mark.approval_status,
            "reviewing_teacher_id": current_teacher.id
        }

        db.flush()

        log_final_mark_action(
            db=db,
            teacher_id=current_teacher.id,
            action="UPDATE",
            final_mark_id=existing_mark.id,
            previous_value=prev_data,
            updated_value=updated_data,
            reason=review_in.reason
        )
        return existing_mark

    new_mark = FinalMark(
        answer_id=review_in.answer_id,
        approved_marks=review_in.approved_marks,
        reviewing_teacher_id=current_teacher.id,
        approval_status=review_in.approval_status,
        approval_timestamp=datetime.now(timezone.utc)
    )
    db.add(new_mark)
    db.flush()

    new_data = {
        "approved_marks": new_mark.approved_marks,
        "approval_status": new_mark.approval_status,
        "reviewing_teacher_id": current_teacher.id
    }

    log_final_mark_action(
        db=db,
        teacher_id=current_teacher.id,
        action="CREATE",
        final_mark_id=new_mark.id,
        previous_value=None,
        updated_value=new_data,
        reason=review_in.reason
    )

    # Check if submission processing_status can be updated to REVIEWED
    all_answers = db.query(StudentAnswer).filter(StudentAnswer.submission_id == submission.id).all()
    reviewed_count = db.query(FinalMark).filter(
        FinalMark.answer_id.in_([a.id for a in all_answers])
    ).count()
    if reviewed_count >= len(all_answers):
        submission.processing_status = "REVIEWED"

    return new_mark


def execute_batch_review_transactional(
    db: Session,
    batch_in: BatchTeacherReviewRequest,
    current_teacher: User,
    auto_commit: bool = True
) -> List[FinalMark]:
    """
    Executes a batch of mark reviews atomically within a database transaction.
    If any single review fails validation, authorization, or persistence, the ENTIRE batch
    is rolled back completely, leaving no partial final marks or orphan audit logs.

    :param db: SQLAlchemy database session.
    :param batch_in: Batch review input schema.
    :param current_teacher: Authenticated teacher requesting mark approval.
    :param auto_commit: If True (default for standalone API endpoints), commits the transaction.
                        If False (for caller-managed transactions), flushes changes within a nested savepoint
                        without committing the caller's outer transaction.
    """
    if not batch_in.reviews:
        return []

    results = []
    try:
        with db.begin_nested():
            for item in batch_in.reviews:
                mark_res = review_single_mark_in_tx(db=db, review_in=item, current_teacher=current_teacher)
                results.append(mark_res)

        if auto_commit:
            db.commit()
        else:
            db.flush()
    except Exception as exc:
        db.rollback()
        raise exc

    return results
