from fastapi import status
from app.models.exam import Exam
from app.models.submission import AnswerSheet
from app.models.enrollment import ExamEnrollment


def test_subject_catalog_listing_and_creation(client, teacher_token_headers, student_token_headers):
    # 1. Student can list subjects (seeds defaults automatically)
    res = client.get("/api/v1/subjects", headers=student_token_headers)
    assert res.status_code == status.HTTP_200_OK
    subjects = res.json()
    assert len(subjects) >= 5
    names = [s["name"] for s in subjects]
    assert "Artificial Intelligence" in names
    assert "Operating Systems" in names

    # 2. Teacher can add a custom subject
    new_sub = client.post(
        "/api/v1/subjects",
        headers=teacher_token_headers,
        json={
            "name": "Cloud Computing & DevOps",
            "code": "CSE450",
            "department": "Computer Science & Engineering",
            "default_semester": 7
        }
    )
    assert new_sub.status_code == status.HTTP_201_CREATED
    assert new_sub.json()["code"] == "CSE450"

    # 3. Duplicate subject name is rejected
    dup_res = client.post(
        "/api/v1/subjects",
        headers=teacher_token_headers,
        json={"name": "Cloud Computing & DevOps", "code": "CSE451"}
    )
    assert dup_res.status_code == status.HTTP_400_BAD_REQUEST


def test_teacher_exam_creation_with_valid_class(client, teacher_token_headers):
    res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Artificial Intelligence Midterm",
            "subject": "Artificial Intelligence",
            "code": "CSE311",
            "semester": 6,
            "section": 2,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain A* Search algorithm.",
                    "model_answer": "Heuristic search algorithm using f(n) = g(n) + h(n).",
                    "max_marks": 5.0
                }
            ]
        }
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["semester"] == 6
    assert data["section"] == 2
    assert data["subject"] == "Artificial Intelligence"
    assert "[CSE311]" in data["title"]


def test_exam_creation_missing_class_fields_rejected(client, teacher_token_headers):
    # Missing semester
    res1 = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "No Semester", "subject": "Math", "section": 1}
    )
    assert res1.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 422)

    # Missing section
    res2 = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "No Section", "subject": "Math", "semester": 6}
    )
    assert res2.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 422)

    # Missing subject
    res3 = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "No Subject", "semester": 6, "section": 1}
    )
    assert res3.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 422)


def test_exam_creation_invalid_section_rejected(client, teacher_token_headers):
    # Section 0
    res0 = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Invalid Sec", "subject": "Math", "semester": 6, "section": 0}
    )
    assert res0.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, 422)

    # Section 5
    res5 = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Invalid Sec", "subject": "Math", "semester": 6, "section": 5}
    )
    assert res5.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, 422)

    # Semester 15 (exceeds max range)
    res_sem = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Invalid Sem", "subject": "Math", "semester": 15, "section": 1}
    )
    assert res_sem.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, 422)


def test_exam_class_cannot_be_changed_after_submissions_exist(client, teacher_token_headers, student_token_headers):
    # 1. Create exam
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Class Freeze Exam", "subject": "CS", "semester": 6, "section": 1}
    )
    exam_id = exam_res.json()["id"]

    # 2. Before submissions exist, teacher can update semester/section
    upd1 = client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"semester": 6, "section": 2}
    )
    assert upd1.status_code == status.HTTP_200_OK
    assert upd1.json()["section"] == 2

    # 3. Student submits an answer sheet
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://freeze_sub.pdf"}
    )
    assert sub_res.status_code == status.HTTP_201_CREATED

    # 4. Teacher attempts to alter semester, section, or subject after submission -> MUST BE REJECTED
    upd_forbidden = client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"section": 3}
    )
    assert upd_forbidden.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been received" in upd_forbidden.json()["detail"]


def test_student_available_exams_and_self_enrollment(client, db, teacher_token_headers, student_token_headers, student_user):
    # Setup student registered class profile: Sem 6, Sec 1
    prof_res = client.put(
        "/api/v1/auth/me/academic-profile",
        headers=student_token_headers,
        json={"semester": 6, "section": 1, "department": "CSE", "roll_number": "CS2026-001"}
    )
    assert prof_res.status_code == status.HTTP_200_OK
    assert prof_res.json()["semester"] == 6
    assert prof_res.json()["section"] == 1

    # Teacher creates Exam A (Sem 6, Sec 1, published)
    exam_a = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Algorithm Design", "subject": "CS", "semester": 6, "section": 1}
    ).json()
    # Publish Exam A
    client.put(f"/api/v1/exams/{exam_a['id']}", headers=teacher_token_headers, json={"status": "PUBLISHED"})

    # Teacher creates Exam B (Sem 6, Sec 2, published)
    exam_b = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Other Section Exam", "subject": "CS", "semester": 6, "section": 2}
    ).json()
    client.put(f"/api/v1/exams/{exam_b['id']}", headers=teacher_token_headers, json={"status": "PUBLISHED"})

    # Teacher creates Exam C (Sem 6, Sec 1, DRAFT - unpublished)
    exam_c = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Draft Quiz", "subject": "CS", "semester": 6, "section": 1}
    ).json()

    # 1. Student queries available exams matching Sem 6, Sec 1
    avail_res = client.get(
        "/api/v1/exams/student/available?semester=6&section=1",
        headers=student_token_headers
    )
    assert avail_res.status_code == status.HTTP_200_OK
    avail_exams = avail_res.json()
    avail_ids = [e["id"] for e in avail_exams]

    # Exam A is present
    assert exam_a["id"] in avail_ids
    # Exam B (Sec 2) is NOT present
    assert exam_b["id"] not in avail_ids
    # Exam C (Draft / Unpublished) is STRICTLY EXCLUDED
    assert exam_c["id"] not in avail_ids

    # 2. Student self-enrolls in Exam A
    enroll_res = client.post(
        f"/api/v1/exams/{exam_a['id']}/self-enroll",
        headers=student_token_headers
    )
    assert enroll_res.status_code == status.HTTP_201_CREATED
    assert "Successfully enrolled" in enroll_res.json()["message"]

    # 3. Duplicate enrollment is rejected
    dup_enroll = client.post(
        f"/api/v1/exams/{exam_a['id']}/self-enroll",
        headers=student_token_headers
    )
    assert dup_enroll.status_code == status.HTTP_400_BAD_REQUEST
    assert "already enrolled" in dup_enroll.json()["detail"].lower()

    # 4. Attempting to self-enroll in draft exam C is rejected
    draft_enroll = client.post(
        f"/api/v1/exams/{exam_c['id']}/self-enroll",
        headers=student_token_headers
    )
    assert draft_enroll.status_code == status.HTTP_400_BAD_REQUEST
    assert "draft/unpublished" in draft_enroll.json()["detail"]

    # 5. Attempting to self-enroll in mismatched section Exam B is rejected
    mismatch_enroll = client.post(
        f"/api/v1/exams/{exam_b['id']}/self-enroll",
        headers=student_token_headers
    )
    assert mismatch_enroll.status_code == status.HTTP_400_BAD_REQUEST
    assert "mismatch" in mismatch_enroll.json()["detail"].lower()

    # 6. Verify enrollment appears in student's my-enrollments
    my_res = client.get("/api/v1/exams/student/my-enrollments", headers=student_token_headers)
    assert my_res.status_code == status.HTTP_200_OK
    my_ids = [e["id"] for e in my_res.json()]
    assert exam_a["id"] in my_ids


def test_student_enrollment_isolation(client, teacher_token_headers, student_token_headers, second_student_token_headers):
    # Exam 1 (Sem 6, Sec 1)
    exam_1 = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Isolation Exam 1", "subject": "CS", "semester": 6, "section": 1}
    ).json()
    client.put(f"/api/v1/exams/{exam_1['id']}", headers=teacher_token_headers, json={"status": "PUBLISHED"})

    # Student 1 enrolls
    client.post(f"/api/v1/exams/{exam_1['id']}/self-enroll", headers=student_token_headers)

    # Student 2 checks their enrollments -> Must NOT see Exam 1
    s2_my_res = client.get("/api/v1/exams/student/my-enrollments", headers=second_student_token_headers)
    s2_ids = [e["id"] for e in s2_my_res.json()]
    assert exam_1["id"] not in s2_ids


def test_teacher_batch_enroll_section(client, teacher_token_headers, student_token_headers, student_user):
    # Set student user to Sem 5, Sec 3
    client.put(
        "/api/v1/auth/me/academic-profile",
        headers=student_token_headers,
        json={"semester": 5, "section": 3}
    )

    exam = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Section Batch Exam", "subject": "CS", "semester": 5, "section": 3}
    ).json()

    # Teacher batch-enrolls entire section
    batch_res = client.post(
        f"/api/v1/exams/{exam['id']}/enroll-section",
        headers=teacher_token_headers,
        json={"semester": 5, "section": 3}
    )
    assert batch_res.status_code == status.HTTP_201_CREATED
    assert batch_res.json()["enrolled_count"] >= 1

    # Verify student is now enrolled
    stud_res = client.get(f"/api/v1/exams/{exam['id']}/students", headers=teacher_token_headers)
    enrolled_ids = [s["id"] for s in stud_res.json()]
    assert student_user.id in enrolled_ids
