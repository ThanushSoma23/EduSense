from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.api.deps import get_current_user, get_current_teacher

router = APIRouter(prefix="/subjects", tags=["Academic Subject Catalog"])

# ==============================================================================
# OFFICIAL SEMESTER SUBJECT CATALOG (SEMESTERS I THROUGH V)
# ==============================================================================
SEMESTER_SUBJECT_CATALOG = [
    # Semester I
    {"name": "Computer Programming", "code": "CS101", "default_semester": 1, "department": "Computer Science & Engineering"},
    {"name": "Digital Design and Electric Circuits", "code": "EC101", "default_semester": 1, "department": "Electronics & Communication Engineering"},
    {"name": "Mathematics I", "code": "MA101", "default_semester": 1, "department": "Mathematics"},
    {"name": "IT Workshop I", "code": "CS102", "default_semester": 1, "department": "Computer Science & Engineering"},
    {"name": "Communication Skills", "code": "HS101", "default_semester": 1, "department": "Humanities & Social Sciences"},
    {"name": "Physical Training I", "code": "PE101", "default_semester": 1, "department": "Physical Education"},

    # Semester II
    {"name": "Data Structures", "code": "CS201", "default_semester": 2, "department": "Computer Science & Engineering"},
    {"name": "Computer Organization and Architecture", "code": "CS202", "default_semester": 2, "department": "Computer Science & Engineering"},
    {"name": "Electronic Circuits", "code": "EC201", "default_semester": 2, "department": "Electronics & Communication Engineering"},
    {"name": "Mathematics II", "code": "MA201", "default_semester": 2, "department": "Mathematics"},
    {"name": "IT Workshop II", "code": "CS203", "default_semester": 2, "department": "Computer Science & Engineering"},

    # Semester III
    {"name": "Design and Analysis of Algorithms", "code": "CS301", "default_semester": 3, "department": "Computer Science & Engineering"},
    {"name": "Operating Systems", "code": "CS302", "default_semester": 3, "department": "Computer Science & Engineering"},
    {"name": "Introduction to Database Management Systems (DBMS)", "code": "CS303", "default_semester": 3, "department": "Computer Science & Engineering"},
    {"name": "Mathematics III (Discrete Mathematics / Probability & Statistics)", "code": "MA301", "default_semester": 3, "department": "Mathematics"},
    {"name": "IT Workshop III", "code": "CS304", "default_semester": 3, "department": "Computer Science & Engineering"},
    {"name": "Science / Environmental Science", "code": "SC301", "default_semester": 3, "department": "Environmental Sciences"},

    # Semester IV
    {"name": "Theory of Computation", "code": "CS401", "default_semester": 4, "department": "Computer Science & Engineering"},
    {"name": "Computer Networks", "code": "CS402", "default_semester": 4, "department": "Computer Science & Engineering"},
    {"name": "Compiler Design", "code": "CS403", "default_semester": 4, "department": "Computer Science & Engineering"},
    {"name": "Object-Oriented Analysis and Design (OOAD)", "code": "CS404", "default_semester": 4, "department": "Computer Science & Engineering"},
    {"name": "Mathematics IV", "code": "MA401", "default_semester": 4, "department": "Mathematics"},
    {"name": "Economics / Management Principles", "code": "HS401", "default_semester": 4, "department": "Humanities & Social Sciences"},

    # Semester V
    {"name": "Software Engineering", "code": "CS501", "default_semester": 5, "department": "Computer Science & Engineering"},
    {"name": "Parallel and Distributed Systems", "code": "CS502", "default_semester": 5, "department": "Computer Science & Engineering"},
    {"name": "Artificial Intelligence", "code": "CS503", "default_semester": 5, "department": "Computer Science & Engineering"},
    {"name": "Soft Computing", "code": "CS504", "default_semester": 5, "department": "Computer Science & Engineering"},
    {"name": "Digital Signal Processing", "code": "EC501", "default_semester": 5, "department": "Electronics & Communication Engineering"},
    {"name": "Quantum Computing", "code": "CS505", "default_semester": 5, "department": "Computer Science & Engineering"},
]

DEFAULT_INITIAL_SUBJECTS = SEMESTER_SUBJECT_CATALOG


def seed_subjects_catalog(db: Session) -> int:
    """
    Idempotently seeds and aligns the standard curriculum subjects for Semesters I through V.
    - Matches existing subjects by name (case-insensitive) to prevent duplicate rows.
    - Updates default_semester and code to align with the official curriculum.
    - Inserts any missing catalog subjects.
    - Preserves all other custom subjects and existing relations.
    Returns the count of inserted or updated subjects.
    """
    modified_count = 0
    for item in SEMESTER_SUBJECT_CATALOG:
        existing = db.query(Subject).filter(Subject.name.ilike(item["name"].strip())).first()
        if existing:
            changed = False
            if existing.default_semester != item["default_semester"]:
                existing.default_semester = item["default_semester"]
                changed = True
            if not existing.code and item.get("code"):
                code_taken = db.query(Subject).filter(Subject.code == item["code"], Subject.id != existing.id).first()
                if not code_taken:
                    existing.code = item["code"]
                    changed = True
            if changed:
                modified_count += 1
        else:
            code_val = item.get("code")
            if code_val:
                code_taken = db.query(Subject).filter(Subject.code == code_val).first()
                if code_taken:
                    code_val = None
            sub = Subject(
                name=item["name"].strip(),
                code=code_val,
                department=item.get("department", "Computer Science & Engineering"),
                default_semester=item["default_semester"],
                is_active=True
            )
            db.add(sub)
            modified_count += 1

    if modified_count > 0:
        db.commit()
    return modified_count


_seed_subjects_if_empty = seed_subjects_catalog


def validate_exam_semester_and_subject(db: Session, semester: int, subject_name: str) -> None:
    """
    Validates that the selected subject belongs to the selected semester when creating or updating an exam.
    - Ensures subject_name is provided.
    - If the subject exists in the catalog with a designated default_semester:
      raises 400 Bad Request if default_semester != semester.
    """
    if not subject_name or not subject_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject is required."
        )

    seed_subjects_catalog(db)

    clean_name = subject_name.strip()
    matched = db.query(Subject).filter(
        Subject.name.ilike(clean_name),
        Subject.is_active == True
    ).first()

    if not matched:
        matched = db.query(Subject).filter(
            Subject.code.ilike(clean_name),
            Subject.is_active == True
        ).first()

    if matched and matched.default_semester is not None:
        if matched.default_semester != semester:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Selected subject '{matched.name}' belongs to Semester {matched.default_semester}, "
                    f"not Semester {semester}."
                )
            )


@router.get("", response_model=List[SubjectResponse])
def list_subjects(
    semester: Optional[int] = Query(None, ge=1, le=12),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the persistent academic subject catalog.
    Optionally filters by academic semester and department.
    """
    seed_subjects_catalog(db)

    query = db.query(Subject).filter(Subject.is_active == True)
    if semester is not None:
        query = query.filter(Subject.default_semester == semester)
    if department:
        query = query.filter(Subject.department.ilike(f"%{department.strip()}%"))

    return query.order_by(Subject.name.asc()).all()


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_teacher: User = Depends(get_current_teacher)
):
    """
    Adds a new persistent subject to the catalog (Teacher only).
    """
    existing = db.query(Subject).filter(Subject.name.ilike(payload.name.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject '{payload.name.strip()}' already exists in the catalog."
        )

    if payload.code:
        existing_code = db.query(Subject).filter(Subject.code.ilike(payload.code.strip())).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subject code '{payload.code.strip()}' is already used by subject '{existing_code.name}'."
            )

    subject = Subject(
        name=payload.name.strip(),
        code=payload.code.strip().upper() if payload.code else None,
        department=payload.department.strip() if payload.department else "Computer Science & Engineering",
        default_semester=payload.default_semester,
        is_active=True
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
