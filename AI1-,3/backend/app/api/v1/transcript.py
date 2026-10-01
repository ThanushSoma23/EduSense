from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_teacher
from app.schemas.schemas import TranscriptUpdate
from app.db.supabase import db
from app.services.embeddings import compute_cosine_similarity
from app.services.concept_coverage import evaluate_concept_coverage_batch
from app.services.marks_suggestion import compute_suggested_marks_range
from app.agents.tools import tool_save_evaluation

router = APIRouter()

@router.patch("/answers/{id}/transcript")
def update_answer_transcript(
    id: str,
    payload: TranscriptUpdate,
    user: dict = Depends(require_teacher)
):
    ans = db.answers.get(id)
    if not ans:
        raise HTTPException(status_code=404, detail="Answer not found.")

    ans["text"] = payload.text
    ans["needs_review"] = False

    # Re-run evaluation for updated text
    question = db.questions.get(ans["question_id"], {})
    model_ans = question.get("model_answer", "")
    concepts = question.get("concepts", [])
    max_m = float(question.get("max_marks", 5.0))

    sim_pct = compute_cosine_similarity(payload.text, model_ans)
    cov_res = evaluate_concept_coverage_batch([{
        "question_id": ans["question_id"],
        "student_answer": payload.text,
        "model_answer": model_ans,
        "concepts": concepts
    }])

    concepts_eval = cov_res[0].get("concepts", []) if cov_res else []
    s_min, s_max = compute_suggested_marks_range(concepts_eval, max_m, 1.0)

    updated_eval = {
        "similarity_percent": sim_pct,
        "concepts": concepts_eval,
        "suggested_marks_min": s_min,
        "suggested_marks_max": s_max,
        "confidence": 1.0,
        "reason": "Re-evaluated following teacher transcript edit.",
        "citations": []
    }

    tool_save_evaluation(id, updated_eval)
    return {"message": "Transcript updated and evaluation refreshed.", "answer": ans, "evaluation": updated_eval}
