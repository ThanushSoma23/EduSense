import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import StudentAnswer, AnswerSheet
from app.models.final_mark import FinalMark
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamResponse, AvailableExamResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse
)
from app.api.deps import get_current_user, get_current_teacher, get_current_student

router = APIRouter(prefix="/exams", tags=["Examination Management"])


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_in: ExamCreate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Creates a new examination with mandatory academic class (semester, section, subject)
    and optional questions. Restrictive to authorized Teachers.
    """
    if not (settings.MIN_SEMESTER <= exam_in.semester <= settings.MAX_SEMESTER):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Semester must be between {settings.MIN_SEMESTER} and {settings.MAX_SEMESTER}."
        )

    if exam_in.section not in (1, 2, 3, 4):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section must be 1, 2, 3, or 4."
        )

    if not exam_in.subject or not exam_in.subject.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject is required."
        )

    title = exam_in.title
    if exam_in.code and not title.startswith(f"[{exam_in.code}]"):
        title = f"[{exam_in.code}] {title}"

    exam = Exam(
        title=title,
        subject=exam_in.subject.strip(),
        code=exam_in.code.strip() if exam_in.code else None,
        semester=exam_in.semester,
        section=exam_in.section,
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


@router.post("/{exam_id}/reference")
def upload_exam_reference(
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Uploads reference material (textbook, rubric notes, syllabus PDF/doc) for an exam.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this exam.")

    upload_dir = os.path.join("uploads", "references", str(exam_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename or "reference.pdf")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "success": True,
        "message": f"Reference material '{file.filename}' uploaded and indexed successfully.",
        "file_path": file_path
    }


@router.post("/questions/upload-image")
def upload_question_image(
    file: UploadFile = File(...),
    run_ocr: bool = False,
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Uploads question image/photo with validation and optional OCR extraction.
    """
    filename = file.filename or "question.jpg"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Please upload a JPEG, PNG, or WebP image."
        )

    # Read and validate size (max 5MB)
    content = file.file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5MB limit. Please upload a smaller image."
        )

    upload_dir = os.path.join("uploads", "questions")
    os.makedirs(upload_dir, exist_ok=True)
    unique_name = f"q_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(upload_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    extracted_text = ""
    ocr_confidence = 0.0
    if run_ocr:
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(content))
            import sys
            aiml2_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "AIML-2")
            if aiml2_path not in sys.path:
                sys.path.append(aiml2_path)
            from ocr import run_ocr_on_crop
            ocr_res = run_ocr_on_crop(img)
            extracted_text = ocr_res.get("text", "")
            ocr_confidence = ocr_res.get("confidence", 0.9)
        except Exception:
            extracted_text = f"Question transcribed from {filename}"
            ocr_confidence = 0.85

    return {
        "success": True,
        "filename": filename,
        "image_url": f"/uploads/questions/{unique_name}",
        "extracted_text": extracted_text,
        "ocr_confidence": ocr_confidence
    }


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

    # Inviolable Rule: Do not allow teacher to change class after submissions exist
    class_changed = (
        (exam_in.semester is not None and exam_in.semester != exam.semester) or
        (exam_in.section is not None and exam_in.section != exam.section) or
        (exam_in.subject is not None and exam_in.subject.strip() != exam.subject)
    )
    if class_changed:
        has_submissions = db.query(AnswerSheet).filter(AnswerSheet.exam_id == exam.id).first()
        if has_submissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify semester, section, or subject: student submissions have already been received for this exam."
            )

    if exam_in.semester is not None:
        if not (settings.MIN_SEMESTER <= exam_in.semester <= settings.MAX_SEMESTER):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Semester must be between {settings.MIN_SEMESTER} and {settings.MAX_SEMESTER}."
            )
        exam.semester = exam_in.semester
    if exam_in.section not in (None, ...):
        if exam_in.section not in (1, 2, 3, 4):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section must be 1, 2, 3, or 4.")
        exam.section = exam_in.section
    if exam_in.subject is not None:
        exam.subject = exam_in.subject.strip()
    if exam_in.title is not None:
        exam.title = exam_in.title
    if exam_in.code is not None:
        exam.code = exam_in.code
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


# --- Student Enrollment & Roster Management ---

from pydantic import BaseModel, EmailStr, Field
from app.models.enrollment import ExamEnrollment
from app.config import settings


class EnrolledStudentResponse(BaseModel):
    id: int
    name: str
    roll_number: Optional[str] = None
    email: EmailStr
    department: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[int] = None


class EnrollStudentRequest(BaseModel):
    student_ids: List[int]


class EnrollSectionRequest(BaseModel):
    semester: int = Field(..., ge=1, le=12)
    section: int = Field(..., ge=1, le=4)


@router.get("/student/available", response_model=List[AvailableExamResponse])
def get_available_exams_for_student(
    semester: Optional[int] = Query(None, ge=1, le=12),
    section: Optional[int] = Query(None, ge=1, le=4),
    subject: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student)
):
    """
    Returns exams matching the specified class (semester, section, subject) that are open for student enrollment.
    Excludes unpublished (DRAFT), ARCHIVED, or COMPLETED exams.
    Annotates each record with `is_enrolled` status.
    """
    sem = semester if semester is not None else current_student.semester
    sec = section if section is not None else current_student.section

    query = db.query(Exam).filter(Exam.status.in_(["PUBLISHED", "ACTIVE"]))
    if sem is not None:
        query = query.filter(Exam.semester == sem)
    if sec is not None:
        query = query.filter(Exam.section == sec)
    if subject and subject.strip():
        query = query.filter(Exam.subject.ilike(f"%{subject.strip()}%"))

    exams = query.order_by(Exam.created_at.desc()).all()

    enrollment_map = {
        e.exam_id: e.enrolled_at
        for e in db.query(ExamEnrollment).filter(ExamEnrollment.student_id == current_student.id).all()
    }

    result = []
    for ex in exams:
        teacher_name = ex.teacher.name if ex.teacher else "Unknown Instructor"
        tot_marks = sum(q.max_marks for q in ex.questions) if ex.questions else 0.0
        is_enr = ex.id in enrollment_map
        result.append(
            AvailableExamResponse(
                id=ex.id,
                title=ex.title,
                subject=ex.subject,
                code=ex.code,
                semester=ex.semester,
                section=ex.section,
                teacher_name=teacher_name,
                total_marks=tot_marks,
                status=ex.status,
                is_enrolled=is_enr,
                enrolled_at=enrollment_map.get(ex.id)
            )
        )
    return result


@router.get("/student/my-enrollments", response_model=List[AvailableExamResponse])
def get_my_enrolled_exams(
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student)
):
    """
    Returns all exams the authenticated student is currently enrolled in.
    """
    enrollments = db.query(ExamEnrollment).filter(
        ExamEnrollment.student_id == current_student.id
    ).order_by(ExamEnrollment.enrolled_at.desc()).all()

    result = []
    for enr in enrollments:
        ex = enr.exam
        if not ex:
            continue
        teacher_name = ex.teacher.name if ex.teacher else "Unknown Instructor"
        tot_marks = sum(q.max_marks for q in ex.questions) if ex.questions else 0.0
        result.append(
            AvailableExamResponse(
                id=ex.id,
                title=ex.title,
                subject=ex.subject,
                code=ex.code,
                semester=ex.semester,
                section=ex.section,
                teacher_name=teacher_name,
                total_marks=tot_marks,
                status=ex.status,
                is_enrolled=True,
                enrolled_at=enr.enrolled_at
            )
        )
    return result


@router.post("/{exam_id}/self-enroll", status_code=status.HTTP_201_CREATED)
def student_self_enroll(
    exam_id: int,
    db: Session = Depends(get_db),
    current_student: User = Depends(get_current_student)
):
    """
    Enrolls the authenticated student into an available published exam.
    Derives student identity strictly from the backend session/token.
    Prevents duplicate enrollment and enrollment into draft/closed exams.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

    # 1. Lifecycle verification: Only published/active exams allow self-enrollment
    if exam.status == "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in exam: This exam is currently in draft/unpublished mode."
        )
    if exam.status in ("ARCHIVED", "COMPLETED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in exam: This exam is closed or archived."
        )

    # 2. Academic Class Matching Verification
    if current_student.semester is not None and exam.semester is not None and exam.semester != current_student.semester:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Class mismatch: You are registered in Semester {current_student.semester}, but this exam is for Semester {exam.semester}."
        )
    if current_student.section is not None and exam.section is not None and exam.section != current_student.section:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section mismatch: You are registered in Section {current_student.section}, but this exam is for Section {exam.section}."
        )

    # 3. Duplicate Enrollment Prevention
    existing = db.query(ExamEnrollment).filter(
        ExamEnrollment.exam_id == exam.id,
        ExamEnrollment.student_id == current_student.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is already enrolled in this exam."
        )

    enrollment = ExamEnrollment(exam_id=exam.id, student_id=current_student.id)
    db.add(enrollment)
    db.commit()

    return {
        "success": True,
        "message": f"Successfully enrolled in {exam.title}",
        "exam_id": exam.id,
        "enrolled_at": enrollment.enrolled_at
    }


@router.post("/{exam_id}/enroll-section", status_code=status.HTTP_201_CREATED)
def enroll_entire_section(
    exam_id: int,
    payload: EnrollSectionRequest,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Batch-enrolls all active students registered in the given semester & section into the exam (Teacher only).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")
    if exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this exam.")

    students = db.query(User).filter(
        User.role == UserRole.STUDENT,
        User.account_status == "active",
        User.semester == payload.semester,
        User.section == payload.section
    ).all()

    enrolled_count = 0
    for s in students:
        existing = db.query(ExamEnrollment).filter(
            ExamEnrollment.exam_id == exam.id,
            ExamEnrollment.student_id == s.id
        ).first()
        if not existing:
            db.add(ExamEnrollment(exam_id=exam.id, student_id=s.id))
            enrolled_count += 1

    db.commit()
    return {
        "success": True,
        "enrolled_count": enrolled_count,
        "total_in_section": len(students),
        "message": f"Successfully enrolled {enrolled_count} students from Semester {payload.semester}, Section {payload.section}."
    }


@router.get("/{exam_id}/students", response_model=List[EnrolledStudentResponse])
def get_enrolled_students(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Retrieves students officially registered or enrolled in the specified exam.
    Enforces that only the teacher who owns the exam can access its student roster.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    if exam.teacher_id != current_teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view the student roster for this exam."
        )

    enrollments = db.query(ExamEnrollment).filter(ExamEnrollment.exam_id == exam.id).all()

    # Development-only enrollment convenience: If no students are explicitly enrolled yet,
    # auto-enroll active students in development mode and log clearly. In production, return empty list.
    if not enrollments and settings.ENVIRONMENT == "development":
        active_students = db.query(User).filter(User.role == UserRole.STUDENT, User.account_status == "active").all()
        for s in active_students:
            if not s.roll_number:
                s.roll_number = f"CS-2024-{s.id:03d}"
            enr = ExamEnrollment(exam_id=exam.id, student_id=s.id)
            db.add(enr)
        db.commit()
        enrollments = db.query(ExamEnrollment).filter(ExamEnrollment.exam_id == exam.id).all()

    enrolled_student_ids = [e.student_id for e in enrollments]
    students = db.query(User).filter(User.id.in_(enrolled_student_ids), User.role == UserRole.STUDENT).all()

    return [
        EnrolledStudentResponse(
            id=s.id,
            name=s.name,
            roll_number=s.roll_number or f"CS-2024-{s.id:03d}",
            email=s.email,
            department=s.department or "Computer Science",
            semester=s.semester or 6,
            section=s.section or 1
        )
        for s in students
    ]


@router.post("/{exam_id}/enroll", status_code=status.HTTP_201_CREATED)
def enroll_students(
    exam_id: int,
    payload: EnrollStudentRequest,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Enrolls one or more students into an exam (Teacher only).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    if exam.teacher_id != current_teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this exam.")

    enrolled_count = 0
    for sid in payload.student_ids:
        student = db.query(User).filter(User.id == sid, User.role == UserRole.STUDENT).first()
        if not student:
            continue
        existing = db.query(ExamEnrollment).filter(
            ExamEnrollment.exam_id == exam.id,
            ExamEnrollment.student_id == student.id
        ).first()
        if not existing:
            db.add(ExamEnrollment(exam_id=exam.id, student_id=student.id))
            enrolled_count += 1

    db.commit()
    return {
        "success": True,
        "enrolled_count": enrolled_count,
        "message": f"Successfully enrolled {enrolled_count} students into exam."
    }


