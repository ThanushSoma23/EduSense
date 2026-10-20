from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.api.deps import get_current_user, get_current_teacher

router = APIRouter(prefix="/subjects", tags=["Academic Subject Catalog"])

DEFAULT_INITIAL_SUBJECTS = [
    {"name": "Artificial Intelligence", "code": "CSE311", "department": "Computer Science & Engineering", "default_semester": 6},
    {"name": "Operating Systems", "code": "CS-302", "department": "Computer Science & Engineering", "default_semester": 4},
    {"name": "Data Structures & Algorithms", "code": "CS-201", "department": "Computer Science & Engineering", "default_semester": 3},
    {"name": "Database Management Systems", "code": "CS-304", "department": "Computer Science & Engineering", "default_semester": 5},
    {"name": "Computer Networks", "code": "CS-401", "department": "Computer Science & Engineering", "default_semester": 5},
    {"name": "Software Engineering", "code": "CS-306", "department": "Computer Science & Engineering", "default_semester": 6},
    {"name": "Machine Learning", "code": "CSE412", "department": "Computer Science & Engineering", "default_semester": 7},
]


def _seed_subjects_if_empty(db: Session) -> None:
    count = db.query(Subject).count()
    if count == 0:
        for item in DEFAULT_INITIAL_SUBJECTS:
            sub = Subject(
                name=item["name"],
                code=item["code"],
                department=item["department"],
                default_semester=item["default_semester"],
                is_active=True
            )
            db.add(sub)
        db.commit()


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
    _seed_subjects_if_empty(db)

    query = db.query(Subject).filter(Subject.is_active == True)
    if semester is not None:
        query = query.filter(
            (Subject.default_semester == semester) | (Subject.default_semester.is_(None))
        )
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
