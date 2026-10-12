"""
EduSense AI - Seed Demo Script
Creates TCP 3-way Handshake Exam, Question, Rubric Concepts, KB passage, and Sample Student Answer.
Allows end-to-end evaluation pipeline execution without requiring raw image OCR.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

from app.db.supabase import db
from app.evaluation.rag_kb import index_document
from app.evaluation.evaluator import evaluate_answer_full

def seed_demo_data():
    print("=" * 60)
    print(" EduSense AI - Demo Seeding (TCP 3-Way Handshake)")
    print("=" * 60)

    exam_id = "exam-tcp-handshake-2026"
    teacher_id = "11111111-1111-1111-1111-111111111111"
    inst_id = "c1111111-1111-1111-1111-111111111111"
    subject_id = "CS-401"

    # 1. Seed Exam
    db.exams[exam_id] = {
        "id": exam_id,
        "title": "Computer Networks Midterm",
        "subject": subject_id,
        "code": "CS-401",
        "teacher_id": teacher_id
    }
    print(f"[OK] Seeded Exam: '{db.exams[exam_id]['title']}'")

    # 2. Seed Question & Rubric Concepts
    q_id = "q-tcp-handshake-101"
    rubric_concepts = [
        {"id": "rc-1", "concept": "Handshake sequence", "weight": 0.30, "status": "covered"},
        {"id": "rc-2", "concept": "SYN packet", "weight": 0.20, "status": "covered"},
        {"id": "rc-3", "concept": "ACK packet", "weight": 0.20, "status": "covered"},
        {"id": "rc-4", "concept": "Sequence-number sync", "weight": 0.15, "status": "partial"},
        {"id": "rc-5", "concept": "Reliable communication", "weight": 0.15, "status": "missing"}
    ]

    db.questions[q_id] = {
        "id": q_id,
        "exam_id": exam_id,
        "number": 1,
        "text": "Describe the TCP three-way handshake procedure and explain its significance in reliable network communication.",
        "max_marks": 10.0,
        "model_answer": "The TCP 3-way handshake establishes a reliable connection. 1. Client sends SYN packet to server. 2. Server replies with SYN-ACK packet. 3. Client sends ACK packet. This synchronizes sequence numbers between endpoints.",
        "concepts": rubric_concepts
    }
    print("[OK] Seeded Question: TCP 3-way Handshake (10 Marks, 5 Rubric Concepts).")

    # 3. Seed KB Document
    kb_passage = (
        "Transmission Control Protocol (TCP) uses a three-way handshake to set up a connection before data transmission. "
        "The handshake steps are: (1) Client sends SYN to request connection, (2) Server responds with SYN-ACK, "
        "(3) Client sends ACK confirming receipt. This process initializes sequence numbers and guarantees reliable data exchange."
    ).encode("utf-8")

    kb_info = index_document(
        file_bytes=kb_passage,
        filename="TCP_IP_Protocol_Guide_Ch4.pdf",
        subject_id=subject_id,
        institution_id=inst_id
    )
    print(f"[OK] Seeded KB Document: '{kb_info['filename']}' ({kb_info['chunks_indexed']} chunks).")

    # 4. Seed Answer Sheet & Student Answer
    sheet_id = "sheet-demo-student-1"
    student_id = "22222222-2222-2222-2222-222222222222"

    db.answer_sheets[sheet_id] = {
        "id": sheet_id,
        "exam_id": exam_id,
        "student_id": student_id,
        "file_url": "https://storage.edusense.ai/sheets/tcp_handshake_student1.pdf",
        "status": "EVALUATED"
    }

    student_ans_text = "TCP connection is initialized using a 3-way handshake. First, client sends a SYN packet to server. Server sends back SYN-ACK. Finally, client sends ACK packet to finish setup and sync sequence number."

    ans_id = "ans-demo-student-1"
    db.answers[ans_id] = {
        "id": ans_id,
        "sheet_id": sheet_id,
        "question_id": q_id,
        "text": student_ans_text,
        "ocr_confidence": 0.95
    }

    # 5. Execute Evaluation
    eval_res = evaluate_answer_full(
        student_answer=student_ans_text,
        model_answer=db.questions[q_id]["model_answer"],
        max_marks=10.0,
        concepts=rubric_concepts,
        institution_id=inst_id,
        subject_id=subject_id
    )

    print("=" * 60)
    print(" DEMO EVALUATION RESULT (AI Suggestion Only - No Final Marks Set)")
    print("=" * 60)
    print(f"Similarity Percentage: {eval_res.similarity_pct}%")
    print(f"AI Suggested Marks Range: [{eval_res.ai_suggested_min} - {eval_res.ai_suggested_max}] / 10.0")
    print(f"AI Confidence Score: {eval_res.ai_confidence}")
    print(f"Rationale: {eval_res.rationale}")
    print(f"Citations: {[f'{c.source} p.{c.page}' for c in eval_res.citations]}")
    print("=" * 60)
    print("SUCCESS: Seed demo data created and end-to-end evaluation executed successfully.")

if __name__ == "__main__":
    seed_demo_data()
