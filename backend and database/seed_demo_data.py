"""
EduSense Seed Script for Local Demonstration
Creates demo teacher, student, exam, questions, and submission in the local database.
"""
from app.database import SessionLocal, Base, engine
from app.security import hash_password
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.models.final_mark import FinalMark

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Teacher account
        teacher = db.query(User).filter(User.email == "teacher@edusense.com").first()
        if not teacher:
            teacher = User(
                name="Prof. Alan Turing",
                email="teacher@edusense.com",
                password_hash=hash_password("Password@123"),
                role=UserRole.TEACHER,
                account_status="active"
            )
            db.add(teacher)
            db.commit()
            db.refresh(teacher)
            print("Created demo teacher: teacher@edusense.com")
        else:
            print("Demo teacher already exists.")

        # 2. Student account
        student = db.query(User).filter(User.email == "student@edusense.com").first()
        if not student:
            student = User(
                name="Alice Student",
                email="student@edusense.com",
                password_hash=hash_password("Password@123"),
                role=UserRole.STUDENT,
                account_status="active"
            )
            db.add(student)
            db.commit()
            db.refresh(student)
            print("Created demo student: student@edusense.com")
        else:
            print("Demo student already exists.")

        # 3. Demo Exam
        exam = db.query(Exam).filter(Exam.title == "Data Structures & Algorithms Midterm").first()
        if not exam:
            exam = Exam(
                title="Data Structures & Algorithms Midterm",
                subject="Computer Science",
                teacher_id=teacher.id,
                status="PUBLISHED"
            )
            db.add(exam)
            db.commit()
            db.refresh(exam)

            # Questions
            q1 = Question(
                exam_id=exam.id,
                question_number=1,
                question_text="Explain the time complexity of QuickSort in best, average, and worst cases with justifications.",
                model_answer="QuickSort best case is O(n log n) with balanced partitioning. Average case is O(n log n) across random pivots. Worst case is O(n^2) when already sorted or reversed and pivot is an extreme element.",
                max_marks=10.0,
                rubric="Accuracy of time complexities: 4 marks; Justification: 6 marks."
            )
            q2 = Question(
                exam_id=exam.id,
                question_number=2,
                question_text="What is an AVL Tree and how does self-balancing maintain O(log n) search time?",
                model_answer="An AVL Tree is a self-balancing binary search tree where the height difference between left and right subtrees (balance factor) is at most 1. Rotations (LL, RR, LR, RL) rebalance the tree upon insertion/deletion.",
                max_marks=10.0,
                rubric="Definition: 4 marks; Rotations explanation: 6 marks."
            )
            db.add_all([q1, q2])
            db.commit()
            print("Created demo exam with 2 questions.")
        else:
            print("Demo exam already exists.")

        # 4. Demo Submission
        submission = db.query(AnswerSheet).filter(
            AnswerSheet.student_id == student.id,
            AnswerSheet.exam_id == exam.id
        ).first()
        if not submission:
            submission = AnswerSheet(
                student_id=student.id,
                exam_id=exam.id,
                file_reference="uploads/student_alice_dsa_midterm.pdf",
                processing_status="EXTRACTED"
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)

            # Answers extracted via OCR
            ans1 = StudentAnswer(
                submission_id=submission.id,
                question_id=exam.questions[0].id,
                extracted_text="QuickSort best case is O(n log n) and average is O(n log n). Worst case occurs when already sorted, giving O(n^2).",
                ocr_confidence=0.96,
                extraction_status="SUCCESS"
            )
            ans2 = StudentAnswer(
                submission_id=submission.id,
                question_id=exam.questions[1].id,
                extracted_text="AVL Tree maintains balance factor between -1 and 1 using LL, RR, LR, RL rotations to guarantee O(log n) search time.",
                ocr_confidence=0.94,
                extraction_status="SUCCESS"
            )
            db.add_all([ans1, ans2])
            db.commit()
            print("Created demo submission with OCR answers.")
        else:
            print("Demo submission already exists.")

        print("\nSeed completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
