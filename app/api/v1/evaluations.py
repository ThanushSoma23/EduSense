import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import StudentAnswer, AnswerSheet
from app.models.evaluation import Evaluation
from app.schemas.evaluation import EvaluationCreate, EvaluationUpdate, EvaluationResponse
from app.api.deps import get_current_user, get_current_user_optional

router = APIRouter(prefix="/evaluations", tags=["Evaluation Data Integration"])


@router.post("", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
def store_evaluation(
    eval_in: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_service_key: Optional[str] = Header(None, alias="X-Service-Key")
):
    """
    Receives evaluation results from the trusted AI evaluation engine or exam teacher.
    Protects service ingestion credentials and verifies numeric score bounds.
    """
    # 1. Fetch StudentAnswer
    answer = db.query(StudentAnswer).filter(StudentAnswer.id == eval_in.answer_id).first()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student answer not found")

    question = db.query(Question).filter(Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated question not found")

    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated exam not found")

    # Cross-exam relationship validation
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == answer.submission_id).first()
    if not submission or submission.exam_id != exam.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data integrity violation: Answer belongs to a question from a different exam."
        )

    # 2. Authorization Check (Service Key OR Authorized Exam Teacher)
    is_trusted_service = bool(
        x_service_key and
        settings.EVALUATION_SERVICE_KEY and
        secrets.compare_digest(x_service_key, settings.EVALUATION_SERVICE_KEY)
    )
    is_authorized_teacher = (current_user and current_user.role == UserRole.TEACHER and exam.teacher_id == current_user.id)

    if not (is_trusted_service or is_authorized_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Only trusted AI evaluation service engines or exam teachers can submit evaluations."
        )

    # 3. Numeric range validations
    if eval_in.similarity_score is not None and not (0.0 <= eval_in.similarity_score <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Similarity score must be between 0.0 and 1.0."
        )

    if eval_in.concept_coverage is not None and not (0.0 <= eval_in.concept_coverage <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Concept coverage must be between 0.0 and 1.0."
        )

    if eval_in.suggested_marks < 0.0 or eval_in.suggested_marks > question.max_marks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Suggested marks ({eval_in.suggested_marks}) must be between 0.0 and maximum marks ({question.max_marks})."
        )

    # 4. Upsert Evaluation record inside atomic transaction
    existing_eval = db.query(Evaluation).filter(Evaluation.answer_id == eval_in.answer_id).first()
    if existing_eval:
        existing_eval.similarity_score = eval_in.similarity_score
        existing_eval.concept_coverage = eval_in.concept_coverage
        existing_eval.suggested_marks = eval_in.suggested_marks
        existing_eval.feedback = eval_in.feedback
        existing_eval.supporting_references = eval_in.supporting_references
        existing_eval.evaluation_status = eval_in.evaluation_status
        db.commit()
        db.refresh(existing_eval)
        return existing_eval

    evaluation = Evaluation(
        answer_id=eval_in.answer_id,
        similarity_score=eval_in.similarity_score,
        concept_coverage=eval_in.concept_coverage,
        suggested_marks=eval_in.suggested_marks,
        feedback=eval_in.feedback,
        supporting_references=eval_in.supporting_references,
        evaluation_status=eval_in.evaluation_status
    )
    db.add(evaluation)

    if submission.processing_status in ["PENDING", "EXTRACTED"]:
        submission.processing_status = "EVALUATED"

    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/answer/{answer_id}", response_model=EvaluationResponse)
def get_evaluation_by_answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves AI evaluation details for a specific student answer.
    Restricts access to authorized student or exam teacher.
    """
    answer = db.query(StudentAnswer).filter(StudentAnswer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student answer not found")

    submission = db.query(AnswerSheet).filter(AnswerSheet.id == answer.submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()

    # Access control
    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if current_user.role == UserRole.TEACHER and exam and exam.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Exam was created by another teacher."
        )

    evaluation = db.query(Evaluation).filter(Evaluation.answer_id == answer_id).first()
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI Evaluation result not found (Status: PENDING or UNAVAILABLE)."
        )

    return evaluation


@router.get("/submission/{submission_id}", response_model=List[EvaluationResponse])
def get_evaluations_by_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all AI evaluations for a submission.
    Restricts access to authorized student or exam teacher.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()

    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if current_user.role == UserRole.TEACHER and exam and exam.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Exam was created by another teacher."
        )

    answers = db.query(StudentAnswer.id).filter(StudentAnswer.submission_id == submission_id).all()
    answer_ids = [a.id for a in answers]

    evaluations = db.query(Evaluation).filter(Evaluation.answer_id.in_(answer_ids)).all()
    return evaluations
