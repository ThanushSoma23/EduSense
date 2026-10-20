import os
import mimetypes
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.models.final_mark import FinalMark
from app.schemas.submission import (
    AnswerSheetCreate, AnswerSheetUpdate, AnswerSheetResponse,
    StudentAnswerCreate, StudentAnswerResponse,
    TranscribeSubmissionResponse, TranscribedAnswerItem
)
from app.api.deps import get_current_user, get_current_user_optional, get_current_teacher
from app.security import decode_access_token
from app.services.ocr_service import transcribe_and_segment, get_last_ocr_error
from app.services.storage_service import get_storage_service
from app.services.pipeline_service import run_evaluation_aiml3, process_submission_pipeline

class TeacherAnswerCorrectionPayload(BaseModel):
    extracted_text: str = Field(..., description="Teacher-corrected student answer transcript")


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


@router.get("/{submission_id}/file")
def get_submission_file(
    submission_id: int,
    token: Optional[str] = Query(None, description="Optional JWT token for inline browser embedding"),
    db: Session = Depends(get_db),
    current_user_opt: Optional[User] = Depends(get_current_user_optional)
):
    """
    Secure authenticated endpoint to download or preview the submitted answer sheet.
    Supports either Authorization header Bearer token or token query param (for iframes/images).
    Enforces authorization:
    - Students can only view their own submissions.
    - Teachers can only view submissions for exams they own.
    - Prevents public unauthenticated access to student submissions.
    """
    user = current_user_opt
    if user is None and token:
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            try:
                user = db.query(User).filter(User.id == int(payload["sub"])).first()
            except Exception:
                pass

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to access submission file.")

    if user.account_status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive or suspended.")

    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated exam not found")

    if user.role == UserRole.STUDENT and submission.student_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot access another student's submission file.")

    if user.role == UserRole.TEACHER and exam.teacher_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Exam was created by another teacher.")

    if not submission.file_reference:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No file associated with this submission.")

    storage = get_storage_service()
    file_bytes = storage.retrieve(submission.file_reference)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission file could not be retrieved from storage.")

    content_type, _ = mimetypes.guess_type(submission.file_reference)
    if not content_type:
        content_type = "application/pdf" if submission.file_reference.lower().endswith(".pdf") else "image/jpeg"

    ext = os.path.splitext(submission.file_reference)[1] or (".pdf" if content_type == "application/pdf" else ".jpg")
    filename = f"submission_{submission_id}{ext}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Type": content_type
        }
    )


@router.get("/{submission_id}/review")
def get_submission_review_workspace(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified Teacher Review Workspace Endpoint:
    Provides exam details, student details, questions, OCR transcripts, AI evidence,
    dynamic rubric concepts, and awarded marks in a single synchronized payload.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {submission_id} not found.")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated exam not found.")

    # Authorization
    if current_user.role == UserRole.TEACHER and exam.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to review submissions for another teacher's exam."
        )

    student = db.query(User).filter(User.id == submission.student_id).first()
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.question_number).all()

    question_items = []
    for q in questions:
        st_ans = db.query(StudentAnswer).filter(
            StudentAnswer.submission_id == submission.id,
            StudentAnswer.question_id == q.id
        ).first()

        eval_rec = db.query(Evaluation).filter(Evaluation.answer_id == st_ans.id).first() if st_ans else None
        final_rec = db.query(FinalMark).filter(FinalMark.answer_id == st_ans.id).first() if st_ans else None

        extracted_text = (st_ans.extracted_text or "") if st_ans else ""
        ocr_conf = float(st_ans.ocr_confidence) if (st_ans and st_ans.ocr_confidence is not None) else 0.0
        ext_status = st_ans.extraction_status if st_ans else "UNANSWERED"

        needs_review = (
            ext_status in ["PARTIAL", "AMBIGUOUS", "FAILED", "UNANSWERED"] or
            ocr_conf < 0.70 or
            len(extracted_text) < 5 or
            (eval_rec and eval_rec.evaluation_status == "REQUIRES_VERIFICATION")
        )

        # Dynamic rubric concept extraction
        rubric_text = q.rubric or ""
        model_text = q.model_answer or ""
        student_lower = extracted_text.lower()

        raw_criteria = [c.strip() for c in rubric_text.replace(";", "\n").split("\n") if c.strip() and len(c.strip()) > 3]
        if not raw_criteria:
            raw_criteria = [s.strip() for s in model_text.replace(";", ".").split(".") if s.strip() and len(s.strip()) > 8][:4]

        concepts = []
        for crit in raw_criteria:
            crit_words = [w.lower().strip(',.():;\"\'') for w in crit.split() if len(w) > 4]
            matched_count = sum(1 for w in crit_words if w in student_lower)
            if not extracted_text:
                status_label = "missing"
                justification = "Answer area appears blank or unattempted."
            elif matched_count >= max(1, len(crit_words) * 0.45):
                status_label = "covered"
                justification = f"Concept demonstrated in student handwriting."
            elif matched_count > 0:
                status_label = "partial"
                justification = f"Related terms mentioned ({matched_count}/{len(crit_words)} terms)."
            else:
                status_label = "missing"
                justification = "Key concept criteria absent from extracted text."

            concepts.append({
                "label": crit[:60] + ("..." if len(crit) > 60 else ""),
                "status": status_label,
                "justification": justification
            })

        # Final mark details if already awarded
        final_mark_data = None
        if final_rec:
            rev_teacher = db.query(User).filter(User.id == final_rec.reviewing_teacher_id).first()
            final_mark_data = {
                "id": final_rec.id,
                "approved_marks": final_rec.approved_marks,
                "approval_status": final_rec.approval_status,
                "reviewing_teacher_id": final_rec.reviewing_teacher_id,
                "reviewing_teacher_name": rev_teacher.name if rev_teacher else "Teacher",
                "approval_timestamp": final_rec.approval_timestamp.isoformat() if final_rec.approval_timestamp else None
            }

        question_items.append({
            "id": q.id,
            "number": q.question_number,
            "text": q.question_text,
            "max_marks": q.max_marks,
            "model_answer": q.model_answer,
            "rubric": q.rubric,
            "student_answer": {
                "id": st_ans.id if st_ans else None,
                "extracted_text": extracted_text,
                "ocr_confidence": ocr_conf,
                "extraction_status": ext_status,
                "needs_review": needs_review
            },
            "evaluation": {
                "id": eval_rec.id if eval_rec else None,
                "similarity_score": eval_rec.similarity_score if eval_rec else None,
                "concept_coverage": eval_rec.concept_coverage if eval_rec else None,
                "suggested_marks": eval_rec.suggested_marks if eval_rec else 0.0,
                "feedback": eval_rec.feedback if eval_rec else None,
                "evaluation_status": eval_rec.evaluation_status if eval_rec else "PENDING"
            },
            "concepts": concepts,
            "final_mark": final_mark_data
        })

    return {
        "exam": {
            "id": exam.id,
            "title": exam.title,
            "subject": exam.subject,
            "code": exam.code or "EXAM",
            "semester": exam.semester,
            "section": exam.section,
            "status": exam.status
        },
        "student": {
            "id": student.id if student else submission.student_id,
            "name": student.name if student else "Unknown Student",
            "roll_number": student.roll_number if student else f"STU-{submission.student_id}",
            "email": student.email if student else ""
        },
        "submission": {
            "id": submission.id,
            "exam_id": submission.exam_id,
            "student_id": submission.student_id,
            "file_reference": submission.file_reference,
            "submission_time": submission.submission_time.isoformat() if submission.submission_time else None,
            "processing_status": submission.processing_status,
            "file_url": f"/api/v1/submissions/{submission.id}/file"
        },
        "questions": question_items
    }


@router.put("/{submission_id}/answers/{answer_id}")
def correct_student_answer(
    submission_id: int,
    answer_id: int,
    payload: TeacherAnswerCorrectionPayload,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Teacher OCR Correction Endpoint:
    Allows teachers to directly correct OCR-extracted handwriting text before or during review.
    Re-evaluates the corrected text against question rubric, updating suggested marks dynamically.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to correct answers for another teacher's exam."
        )

    st_ans = db.query(StudentAnswer).filter(
        StudentAnswer.id == answer_id,
        StudentAnswer.submission_id == submission.id
    ).first()

    if not st_ans:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student answer not found.")

    q = db.query(Question).filter(Question.id == st_ans.question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    # Apply teacher correction
    st_ans.extracted_text = payload.extracted_text.strip()
    st_ans.extraction_status = "CORRECTED"

    # Re-evaluate with AIML-3 using corrected transcript
    sim, cov, marks, feedback = run_evaluation_aiml3(
        student_text=st_ans.extracted_text,
        model_answer=q.model_answer,
        rubric=q.rubric or "",
        max_marks=q.max_marks
    )

    ev = db.query(Evaluation).filter(Evaluation.answer_id == st_ans.id).first()
    if ev:
        ev.similarity_score = sim
        ev.concept_coverage = cov
        ev.suggested_marks = marks
        ev.feedback = f"Teacher Corrected: {feedback}"
        ev.evaluation_status = "COMPLETED"
    else:
        ev = Evaluation(
            answer_id=st_ans.id,
            similarity_score=sim,
            concept_coverage=cov,
            suggested_marks=marks,
            feedback=f"Teacher Corrected: {feedback}",
            evaluation_status="COMPLETED"
        )
        db.add(ev)

    db.commit()
    db.refresh(st_ans)
    db.refresh(ev)

    return {
        "success": True,
        "message": "Answer text updated and re-evaluated successfully.",
        "answer": {
            "id": st_ans.id,
            "extracted_text": st_ans.extracted_text,
            "extraction_status": st_ans.extraction_status,
            "ocr_confidence": st_ans.ocr_confidence
        },
        "evaluation": {
            "similarity_score": ev.similarity_score,
            "concept_coverage": ev.concept_coverage,
            "suggested_marks": ev.suggested_marks,
            "feedback": ev.feedback,
            "evaluation_status": ev.evaluation_status
        }
    }


@router.post("/{submission_id}/reprocess")
def reprocess_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Reruns the OCR and evaluation pipeline for a submission using the updated EasyOCR pipeline.
    Preserves data integrity and allows recovering previously failed submissions.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam or exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    storage = get_storage_service()
    file_bytes = storage.retrieve(submission.file_reference)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission file not found in storage.")

    created_answers = process_submission_pipeline(
        db=db,
        submission=submission,
        exam=exam,
        image_bytes=file_bytes
    )

    return {
        "success": True,
        "message": f"Reprocessed {len(created_answers)} questions successfully.",
        "status": submission.processing_status
    }



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


@router.post("/{submission_id}/transcribe", response_model=TranscribeSubmissionResponse)
async def transcribe_submission(
    submission_id: int,
    file: Optional[UploadFile] = File(None, description="Optional uploaded image file. If omitted, uses submission.file_reference"),
    backend: Optional[str] = Query(default=None, description="OCR backend: trocr, mock, or auto"),
    threshold: float = Query(default=0.70, ge=0.0, le=1.0, description="Confidence review threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Invokes handwritten OCR and question segmentation for an answer sheet submission.
    1. Authenticates & authorizes student (owner) or teacher (exam creator).
    2. Validates and reads uploaded image bytes or file_reference from storage.
    3. Runs OCR and question-wise segmentation.
    4. Upserts segmented student answers into PostgreSQL associated with the exam questions.
    5. Returns transcribed answer items, confidence scores, and review flags.
    """
    submission = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated exam not found")

    # Authorization
    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot transcribe another student's submission.")

    if current_user.role == UserRole.TEACHER and exam.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Exam was created by another teacher.")

    # Image bytes retrieval
    image_bytes = b""
    if file is not None and file.filename:
        valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")
        if not file.filename.lower().endswith(valid_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image format. Allowed: {', '.join(valid_exts)}"
            )
        image_bytes = await file.read()
    elif submission.file_reference:
        storage = get_storage_service()
        retrieved = storage.retrieve(submission.file_reference)
        if retrieved is not None:
            image_bytes = retrieved
        else:
            import os
            sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "AIML-2", "sample", "answer_sheet.jpg")
            if os.path.exists(sample_path):
                with open(sample_path, "rb") as f:
                    image_bytes = f.read()

    # Invoke OCR and segmentation
    segmented_items, backend_used = transcribe_and_segment(image_bytes, threshold=threshold, backend=backend)
    ocr_error = get_last_ocr_error()
    is_ocr_failure = ocr_error is not None

    # Associate segmented items with questions
    exam_questions = db.query(Question).filter(Question.exam_id == submission.exam_id).order_by(Question.question_number).all()
    q_by_num = {q.question_number: q for q in exam_questions}

    transcribed_answers = []

    if is_ocr_failure:
        submission.processing_status = "FAILED"
        for q in exam_questions:
            existing = db.query(StudentAnswer).filter(
                StudentAnswer.submission_id == submission.id,
                StudentAnswer.question_id == q.id
            ).first()

            if existing:
                existing.extracted_text = ""
                existing.ocr_confidence = 0.0
                existing.extraction_status = "FAILED"
            else:
                new_ans = StudentAnswer(
                    submission_id=submission.id,
                    question_id=q.id,
                    extracted_text="",
                    ocr_confidence=0.0,
                    extraction_status="FAILED"
                )
                db.add(new_ans)

            transcribed_answers.append(
                TranscribedAnswerItem(
                    question_number=q.question_number,
                    question_id=q.id,
                    extracted_text="",
                    ocr_confidence=0.0,
                    needs_review=True,
                    extraction_status="FAILED"
                )
            )

        db.commit()

        return TranscribeSubmissionResponse(
            submission_id=submission.id,
            processing_status="FAILED",
            total_questions=len(transcribed_answers),
            answers=transcribed_answers,
            overall_confidence=0.0,
            needs_review=True,
            backend_used=backend_used
        )

    for item in segmented_items:
        q_num = item["question_number"]
        question = q_by_num.get(q_num)
        if not question and 0 <= q_num - 1 < len(exam_questions):
            question = exam_questions[q_num - 1]

        q_id = question.id if question else None
        extracted_text = item.get("text", "")
        ocr_conf = float(item.get("confidence", 0.0))
        needs_rev = bool(item.get("needs_review", False))

        status_label = item.get("extraction_status", "PARTIAL" if needs_rev else "SUCCESS")
        if needs_rev and status_label == "SUCCESS":
            status_label = "PARTIAL"

        if q_id:
            existing = db.query(StudentAnswer).filter(
                StudentAnswer.submission_id == submission.id,
                StudentAnswer.question_id == q_id
            ).first()

            if existing:
                existing.extracted_text = extracted_text
                existing.ocr_confidence = ocr_conf
                existing.extraction_status = status_label
            else:
                new_ans = StudentAnswer(
                    submission_id=submission.id,
                    question_id=q_id,
                    extracted_text=extracted_text,
                    ocr_confidence=ocr_conf,
                    extraction_status=status_label
                )
                db.add(new_ans)

        transcribed_answers.append(
            TranscribedAnswerItem(
                question_number=q_num,
                question_id=q_id,
                extracted_text=extracted_text,
                ocr_confidence=ocr_conf,
                needs_review=needs_rev,
                extraction_status=status_label
            )
        )

    # Update submission status
    submission.processing_status = "EXTRACTED"
    db.commit()

    all_confs = [a.ocr_confidence for a in transcribed_answers]
    overall_conf = round(sum(all_confs) / len(all_confs), 4) if all_confs else 1.0
    any_needs_rev = any(a.needs_review for a in transcribed_answers)

    return TranscribeSubmissionResponse(
        submission_id=submission.id,
        processing_status="EXTRACTED",
        total_questions=len(transcribed_answers),
        answers=transcribed_answers,
        overall_confidence=overall_conf,
        needs_review=any_needs_rev,
        backend_used=backend_used
    )
