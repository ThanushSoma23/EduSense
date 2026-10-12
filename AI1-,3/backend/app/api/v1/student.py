from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_student
from app.db.supabase import db

router = APIRouter()

@router.get("/student/results")
def get_student_results(user: dict = Depends(require_student)):
    student_id = user.get("id", "22222222-2222-2222-2222-222222222222")

    student_sheets = [s for s in db.answer_sheets.values() if s.get("student_id") == student_id]

    results = []
    for sheet in student_sheets:
        exam_id = sheet["exam_id"]
        # Filter for published exams ONLY
        published = any(p for p in db.publications.values() if p.get("exam_id") == exam_id)
        if not published:
            continue

        exam = db.exams.get(exam_id, {})
        answers = [a for a in db.answers.values() if a.get("sheet_id") == sheet["id"]]

        answer_breakdown = []
        total_awarded = 0.0
        total_max = 0.0

        for ans in answers:
            q = db.questions.get(ans["question_id"], {})
            m = next((m for m in db.marks.values() if m.get("answer_id") == ans["id"]), {})
            ev = next((e for e in db.evaluations.values() if e.get("answer_id") == ans["id"]), {})

            awarded = m.get("final_marks", 0.0) or 0.0
            max_m = float(q.get("max_marks", 5.0))
            total_awarded += awarded
            total_max += max_m

            answer_breakdown.append({
                "question": q,
                "answer": ans,
                "evaluation": ev,
                "mark": m
            })

        results.append({
            "exam": exam,
            "sheet": sheet,
            "score": round(total_awarded, 2),
            "max_score": round(total_max, 2),
            "breakdown": answer_breakdown
        })

    return {"results": results}
