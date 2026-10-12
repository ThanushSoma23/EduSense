from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_teacher
from app.schemas.schemas import AwardMarksRequest
from app.db.supabase import db

router = APIRouter()

@router.post("/marks/{answer_id}/award")
def award_final_marks(
    answer_id: str,
    payload: AwardMarksRequest,
    user: dict = Depends(require_teacher)
):
    """
    INVARIANT ENFORCEMENT LAYER 1:
    The ONLY code path in the entire system that writes `final_marks`.
    Guarded by `require_teacher` dependency.
    """
    ans = db.answers.get(answer_id)
    if not ans:
        raise HTTPException(status_code=404, detail="Answer not found.")

    question = db.questions.get(ans.get("question_id"))
    if not question:
        raise HTTPException(status_code=404, detail="Question associated with answer not found.")

    max_marks = float(question.get("max_marks", 5.0))
    if payload.final_marks < 0 or payload.final_marks > max_marks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mark value {payload.final_marks}. Final marks must be between 0 and {max_marks}."
        )

    teacher_id = user.get("id") or "11111111-1111-1111-1111-111111111111"

    if hasattr(db, "award_marks"):
        mark_record = db.award_marks(
            answer_id=answer_id,
            final_marks=payload.final_marks,
            awarded_by=teacher_id,
            award_source=payload.award_source,
            remarks=payload.remarks
        )
    else:
        # Supabase Python client direct write
        res = db.table("marks").upsert({
            "answer_id": answer_id,
            "final_marks": payload.final_marks,
            "awarded_by": teacher_id,
            "award_source": payload.award_source,
            "remarks": payload.remarks
        }).execute()
        mark_record = res.data[0] if res.data else {}

    return {"message": "Final marks awarded successfully", "mark": mark_record}
