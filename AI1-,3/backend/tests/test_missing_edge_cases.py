import pytest
from app.evaluation.evaluator import (
    compute_marks_range,
    evaluate_answer_full
)
from app.evaluation.rag_kb import hybrid_retrieve, index_document
from app.evaluation.interfaces import MockEmbedder, mock_vector_store
from app.agents.tools import tool_update_sheet_status
from app.db.supabase import db

def test_idempotent_rerun_returns_cached_result():
    """Verify that rerunning evaluation on identical input returns identical cached/idempotent result."""
    concepts = [{"concept": "c1", "weight": 1.0, "status": "covered"}]

    res1 = evaluate_answer_full(
        student_answer="Same student answer",
        model_answer="Same student answer",
        max_marks=5.0,
        concepts=concepts,
        institution_id="inst-idemp",
        subject_id="CS-101"
    )
    res2 = evaluate_answer_full(
        student_answer="Same student answer",
        model_answer="Same student answer",
        max_marks=5.0,
        concepts=concepts,
        institution_id="inst-idemp",
        subject_id="CS-101"
    )

    assert res1.similarity_pct == res2.similarity_pct
    assert res1.ai_suggested_min == res2.ai_suggested_min
    assert res1.ai_suggested_max == res2.ai_suggested_max

def test_resumable_pipeline_from_failed_stage():
    """Verify sheet status and failed_stage recording for pipeline resumption."""
    sheet_id = "sheet-fail-resuma"
    db.answer_sheets[sheet_id] = {"id": sheet_id, "status": "FAILED", "failed_stage": "PREPROCESSED"}

    # Update sheet state to resume
    updated = tool_update_sheet_status(sheet_id, "EVALUATING", failed_stage=None)
    assert updated["status"] == "EVALUATING"
    assert updated.get("failed_stage") is None

def test_empty_answer_returns_none_suggested_marks():
    """Verify empty answer returns ai_suggested_min/max = None."""
    res = evaluate_answer_full(
        student_answer="  ",
        model_answer="Proper answer",
        max_marks=5.0,
        concepts=[{"concept": "c1", "weight": 1.0}],
        institution_id="inst-1",
        subject_id="CS-101"
    )
    assert res.ai_suggested_min is None
    assert res.ai_suggested_max is None
    assert "needs_human_review" in res.flags

def test_missing_kb_graceful_fallback():
    """Verify evaluation runs smoothly when no KB documents exist for tenant."""
    res = evaluate_answer_full(
        student_answer="Student answer without KB",
        model_answer="Model answer",
        max_marks=5.0,
        concepts=[{"concept": "c1", "weight": 1.0}],
        institution_id="non-existent-inst-kb",
        subject_id="NON-EXISTENT-SUBJ"
    )
    assert res.citations == []
    assert res.similarity_pct >= 0.0

def test_low_confidence_widening_and_flags():
    """Verify low confidence (< 0.5) widens band half-width to 1.5 and adds 'low_confidence' flag."""
    s_min, s_max, flags = compute_marks_range(coverage=0.5, max_marks=10.0, confidence=0.3)
    assert "low_confidence" in flags
    # Centre = 5.0, half_width = 1.5 -> min = 3.5, max = 6.5
    assert s_min == 3.5
    assert s_max == 6.5

def test_rrf_reciprocal_rank_fusion_ordering():
    """Verify Reciprocal Rank Fusion ranks chunks correctly."""
    embedder = MockEmbedder()
    index_document(
        file_bytes=b"TCP Handshake Protocol SYN ACK breakdown.",
        filename="tcp_protocol.pdf",
        subject_id="CS-RRF",
        institution_id="inst-rrf",
        embedder=embedder,
        vector_store=mock_vector_store
    )

    chunks = hybrid_retrieve("TCP Handshake", subject_id="CS-RRF", institution_id="inst-rrf", k=1, embedder=embedder, vector_store=mock_vector_store)
    assert len(chunks) == 1
    assert chunks[0]["source"] == "tcp_protocol.pdf"
    assert chunks[0]["score"] > 0.0
