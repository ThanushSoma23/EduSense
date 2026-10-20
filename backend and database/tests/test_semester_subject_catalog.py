import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.subject import Subject
from app.models.exam import Exam
from app.api.v1.subjects import (
    SEMESTER_SUBJECT_CATALOG,
    seed_subjects_catalog,
    validate_exam_semester_and_subject
)

# Expected initial catalog exact definitions for Semesters I through V
EXPECTED_SEMESTER_CATALOG = {
    1: [
        "Computer Programming",
        "Digital Design and Electric Circuits",
        "Mathematics I",
        "IT Workshop I",
        "Communication Skills",
        "Physical Training I",
    ],
    2: [
        "Data Structures",
        "Computer Organization and Architecture",
        "Electronic Circuits",
        "Mathematics II",
        "IT Workshop II",
    ],
    3: [
        "Design and Analysis of Algorithms",
        "Operating Systems",
        "Introduction to Database Management Systems (DBMS)",
        "Mathematics III (Discrete Mathematics / Probability & Statistics)",
        "IT Workshop III",
        "Science / Environmental Science",
    ],
    4: [
        "Theory of Computation",
        "Computer Networks",
        "Compiler Design",
        "Object-Oriented Analysis and Design (OOAD)",
        "Mathematics IV",
        "Economics / Management Principles",
    ],
    5: [
        "Software Engineering",
        "Parallel and Distributed Systems",
        "Artificial Intelligence",
        "Soft Computing",
        "Digital Signal Processing",
        "Quantum Computing",
    ],
}


def test_initial_catalog_completeness_and_exact_mapping(db: Session):
    """
    Verifies that the catalog contains exactly the specified 29 subjects across Semesters 1 through 5
    with no invented subjects for Semesters 6 and above.
    """
    seed_subjects_catalog(db)

    # 1. Verify exact counts per semester
    assert len(EXPECTED_SEMESTER_CATALOG[1]) == 6
    assert len(EXPECTED_SEMESTER_CATALOG[2]) == 5
    assert len(EXPECTED_SEMESTER_CATALOG[3]) == 6
    assert len(EXPECTED_SEMESTER_CATALOG[4]) == 6
    assert len(EXPECTED_SEMESTER_CATALOG[5]) == 6

    total_expected = sum(len(subjs) for subjs in EXPECTED_SEMESTER_CATALOG.values())
    assert total_expected == 29

    for sem, expected_subjects in EXPECTED_SEMESTER_CATALOG.items():
        db_subjects = (
            db.query(Subject)
            .filter(Subject.default_semester == sem, Subject.is_active == True)
            .all()
        )
        db_names = [s.name for s in db_subjects]
        for expected_name in expected_subjects:
            assert expected_name in db_names, f"Missing '{expected_name}' in Semester {sem}"
        assert len(db_subjects) == len(expected_subjects), f"Mismatch in count for Semester {sem}"

    # Semesters 6, 7, 8 must have no default catalog entries
    for empty_sem in [6, 7, 8]:
        empty_subjects = (
            db.query(Subject)
            .filter(Subject.default_semester == empty_sem, Subject.is_active == True)
            .all()
        )
        assert len(empty_subjects) == 0, f"Expected 0 default subjects for Semester {empty_sem}"


def test_catalog_seeding_is_strictly_idempotent(db: Session):
    """
    Verifies that executing seed_subjects_catalog repeatedly does not create duplicates
    and preserves existing custom subjects.
    """
    # 1. Initial seed
    seed_subjects_catalog(db)
    initial_count = db.query(Subject).count()
    assert initial_count >= 29

    # 2. Add a custom teacher-created subject
    custom = Subject(
        name="Advanced Cloud Computing",
        code="CS701",
        default_semester=7,
        department="Computer Science & Engineering",
        is_active=True
    )
    db.add(custom)
    db.commit()

    # 3. Repeated seed execution
    re_seed_count = seed_subjects_catalog(db)
    assert re_seed_count == 0  # No new modifications
    post_count = db.query(Subject).count()
    assert post_count == initial_count + 1

    # Verify custom subject is still intact
    preserved = db.query(Subject).filter(Subject.name == "Advanced Cloud Computing").first()
    assert preserved is not None
    assert preserved.default_semester == 7


def test_subject_api_semester_filtering_endpoint(client, teacher_token_headers):
    """
    Verifies GET /api/v1/subjects?semester=X returns only subjects for the given semester.
    """
    # 1. Semester 1 -> exactly 6 subjects
    res1 = client.get("/api/v1/subjects?semester=1", headers=teacher_token_headers)
    assert res1.status_code == status.HTTP_200_OK
    s1_names = [s["name"] for s in res1.json()]
    assert len(s1_names) == 6
    assert "Computer Programming" in s1_names
    assert "Digital Design and Electric Circuits" in s1_names

    # 2. Semester 3 -> exactly 6 subjects including Operating Systems
    res3 = client.get("/api/v1/subjects?semester=3", headers=teacher_token_headers)
    assert res3.status_code == status.HTTP_200_OK
    s3_names = [s["name"] for s in res3.json()]
    assert len(s3_names) == 6
    assert "Operating Systems" in s3_names
    assert "Design and Analysis of Algorithms" in s3_names
    assert "Computer Programming" not in s3_names

    # 3. Semester 5 -> exactly 6 subjects including Artificial Intelligence
    res5 = client.get("/api/v1/subjects?semester=5", headers=teacher_token_headers)
    assert res5.status_code == status.HTTP_200_OK
    s5_names = [s["name"] for s in res5.json()]
    assert len(s5_names) == 6
    assert "Artificial Intelligence" in s5_names
    assert "Software Engineering" in s5_names

    # 4. Semester 6 -> empty list
    res6 = client.get("/api/v1/subjects?semester=6", headers=teacher_token_headers)
    assert res6.status_code == status.HTTP_200_OK
    assert res6.json() == []


def test_exam_creation_valid_semester_subject_pairs(client, teacher_token_headers):
    """
    Verifies that valid semester-subject pairs can create exams.
    """
    # Semester 3 + Operating Systems
    res_os = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "OS Midterm",
            "subject": "Operating Systems",
            "code": "CS302",
            "semester": 3,
            "section": 1
        }
    )
    assert res_os.status_code == status.HTTP_201_CREATED
    assert res_os.json()["subject"] == "Operating Systems"
    assert res_os.json()["semester"] == 3

    # Semester 5 + Artificial Intelligence
    res_ai = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "AI Midterm",
            "subject": "Artificial Intelligence",
            "code": "CS503",
            "semester": 5,
            "section": 2
        }
    )
    assert res_ai.status_code == status.HTTP_201_CREATED
    assert res_ai.json()["subject"] == "Artificial Intelligence"
    assert res_ai.json()["semester"] == 5


def test_exam_creation_mismatched_semester_subject_rejected(client, teacher_token_headers):
    """
    Verifies that a subject from another semester is strictly rejected with a clear 400 error.
    """
    # Operating Systems belongs to Semester 3. Submitting with Semester 4 must fail.
    res_mismatch = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Invalid Semester Exam",
            "subject": "Operating Systems",
            "semester": 4,
            "section": 1
        }
    )
    assert res_mismatch.status_code == status.HTTP_400_BAD_REQUEST
    assert "Operating Systems" in res_mismatch.json()["detail"]
    assert "Semester 3" in res_mismatch.json()["detail"]
    assert "Semester 4" in res_mismatch.json()["detail"]

    # Artificial Intelligence belongs to Semester 5. Submitting with Semester 1 must fail.
    res_ai_mismatch = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "AI in Sem 1 Invalid",
            "subject": "Artificial Intelligence",
            "semester": 1,
            "section": 1
        }
    )
    assert res_ai_mismatch.status_code == status.HTTP_400_BAD_REQUEST
    assert "Artificial Intelligence" in res_ai_mismatch.json()["detail"]
    assert "Semester 5" in res_ai_mismatch.json()["detail"]


def test_exam_update_semester_subject_validation(client, teacher_token_headers):
    """
    Verifies that updating an exam to a mismatched semester/subject is rejected.
    """
    # 1. Create valid exam in Semester 3
    res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Updatable Exam",
            "subject": "Operating Systems",
            "semester": 3,
            "section": 1
        }
    )
    assert res.status_code == status.HTTP_201_CREATED
    exam_id = res.json()["id"]

    # 2. Update semester to 2 while keeping Operating Systems (Semester 3) -> REJECT
    upd_bad = client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"semester": 2}
    )
    assert upd_bad.status_code == status.HTTP_400_BAD_REQUEST
    assert "Operating Systems" in upd_bad.json()["detail"]

    # 3. Update subject to another Semester 3 subject -> SUCCEED
    upd_good = client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"subject": "Design and Analysis of Algorithms"}
    )
    assert upd_good.status_code == status.HTTP_200_OK
    assert upd_good.json()["subject"] == "Design and Analysis of Algorithms"
