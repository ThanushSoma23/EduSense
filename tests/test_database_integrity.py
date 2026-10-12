import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet
from app.security import hash_password


def test_unique_user_email_constraint(db):
    user1 = User(
        name="Alice",
        email="alice@edusense.edu",
        password_hash=hash_password("secret1"),
        role=UserRole.STUDENT
    )
    db.add(user1)
    db.commit()

    user2 = User(
        name="Alice Duplicate",
        email="alice@edusense.edu",
        password_hash=hash_password("secret2"),
        role=UserRole.STUDENT
    )
    db.add(user2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_exam_cascade_delete_questions(db):
    teacher = User(name="Prof. X", email="profx@edusense.edu", password_hash="hash", role=UserRole.TEACHER)
    db.add(teacher)
    db.commit()

    exam = Exam(title="Physics 101", subject="Physics", teacher_id=teacher.id)
    db.add(exam)
    db.commit()

    q1 = Question(exam_id=exam.id, question_number=1, question_text="What is F=ma?", model_answer="Newton's 2nd Law", max_marks=5.0)
    db.add(q1)
    db.commit()

    assert db.query(Question).filter(Question.exam_id == exam.id).count() == 1

    # Delete exam
    db.delete(exam)
    db.commit()

    # Verify associated questions are cascade deleted
    assert db.query(Question).filter(Question.exam_id == exam.id).count() == 0


def test_duplicate_submission_constraint(db):
    teacher = User(name="Prof. Y", email="profy@edusense.edu", password_hash="hash", role=UserRole.TEACHER)
    student = User(name="Bob", email="bob@edusense.edu", password_hash="hash", role=UserRole.STUDENT)
    db.add_all([teacher, student])
    db.commit()

    exam = Exam(title="Chemistry", subject="Science", teacher_id=teacher.id)
    db.add(exam)
    db.commit()

    sub1 = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://sub1.pdf")
    db.add(sub1)
    db.commit()

    sub2 = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://sub2.pdf")
    db.add(sub2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
