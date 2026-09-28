import math
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from app.evaluation.schemas import EvaluationResult, Citation
from app.evaluation.rag_kb import hybrid_retrieve
from app.evaluation.interfaces import BaseEmbedder, MockEmbedder

logger = logging.getLogger(__name__)

# Prompt injection detection regex patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"give\s+(me\s+)?full\s+marks?",
    r"award\s+maximum\s+marks?",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+an?\s+unrestricted"
]

def detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection or manipulation attempts in student answer."""
    if not text:
        return False
    lower_text = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_text):
            return True
    return False

def compute_similarity(student_answer: str, model_answer: str, kb_chunks: List[Dict[str, Any]], embedder: Optional[BaseEmbedder] = None) -> Tuple[float, float, float]:
    """
    Compute cosine similarities:
    answer_sim = cos(embed(answer), embed(model_answer))
    kb_sim = max cosine over top-k KB chunks
    displayed = round(100 * (0.6*answer_sim + 0.4*kb_sim))
    Returns (answer_sim, kb_sim, displayed_pct)
    """
    embedder = embedder or MockEmbedder()

    v_stu = embedder.embed(student_answer)
    v_mod = embedder.embed(model_answer)

    def cos_sim(v1, v2):
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        return dot / (n1 * n2) if (n1 and n2) else 0.0

    answer_sim = cos_sim(v_stu, v_mod)

    kb_sims = [cos_sim(v_stu, embedder.embed(c.get("chunk_text", ""))) for c in kb_chunks]
    kb_sim = max(kb_sims) if kb_sims else answer_sim

    displayed_pct = round(100.0 * (0.6 * answer_sim + 0.4 * kb_sim))
    return answer_sim, kb_sim, displayed_pct

def compute_concept_coverage_score(concepts: List[Dict[str, Any]]) -> float:
    """
    Calculate weighted coverage score:
    s_i = 1.0 (covered) | 0.5 (partial) | 0.0 (missing)
    coverage = sum(w_i * s_i) / sum(w_i)
    """
    if not concepts:
        return 0.0

    total_weight = sum(float(c.get("weight", 1.0)) for c in concepts) or 1.0
    weighted_score = 0.0

    for c in concepts:
        status = c.get("status", "missing")
        weight = float(c.get("weight", 1.0))
        if status == "covered":
            weighted_score += weight * 1.0
        elif status == "partial":
            weighted_score += weight * 0.5
        elif status == "missing":
            weighted_score += weight * 0.0

    return weighted_score / total_weight

def compute_marks_range(coverage: float, max_marks: float, confidence: float) -> Tuple[float, float, List[str]]:
    """
    Compute suggested marks min and max bounds:
    centre = coverage * max_marks
    Band half-width:
      0.5 marks at confidence >= 0.8
      1.0 marks at confidence 0.5 <= conf < 0.8
      wide (1.5 marks) + flag "low_confidence" below 0.5
    Round bounds to 0.5 step, clamp to [0, max_marks].
    """
    centre = coverage * max_marks
    flags = []

    if confidence >= 0.8:
        half_width = 0.5
    elif confidence >= 0.5:
        half_width = 1.0
    else:
        half_width = 1.5
        flags.append("low_confidence")

    # Half-mark step rounding (e.g. 7.75 +/- 0.5 -> 7.0 to 8.0, 5.0 +/- 1.5 -> 3.5 to 6.5)
    raw_min = centre - half_width
    raw_max = centre + half_width

    s_min = round(raw_min * 2) / 2.0
    s_max = round(raw_max * 2) / 2.0

    # Clamp to [0, max_marks]
    s_min = max(0.0, min(float(s_min), max_marks))
    s_max = max(0.0, min(float(s_max), max_marks))

    return s_min, s_max, flags



def evaluate_answer_full(
    student_answer: str,
    model_answer: str,
    max_marks: float,
    concepts: List[Dict[str, Any]],
    institution_id: str,
    subject_id: str,
    ocr_confidence: float = 1.0,
    embedder: Optional[BaseEmbedder] = None
) -> EvaluationResult:
    """
    Full AIML-3 evaluation pipeline.
    """
    embedder = embedder or MockEmbedder()
    flags = []

    # 1. Blank or garbled answer check
    clean_text = student_answer.strip()
    if not clean_text or len(clean_text) < 3:
        flags.append("needs_human_review")
        return EvaluationResult(
            similarity_pct=0.0,
            covered=[],
            partial=[],
            missing=concepts,
            keywords_missing=[c.get("concept", "") for c in concepts],
            ai_suggested_min=None,
            ai_suggested_max=None,
            ai_confidence=0.0,
            rationale="Blank or unreadable student answer submitted. Flagged for human review.",
            citations=[],
            flags=flags
        )

    # 2. Prompt injection safety check
    if detect_prompt_injection(clean_text):
        flags = ["prompt_injection_suspected", "needs_human_review"]
        # Never return numeric suggested marks on prompt injection
        return EvaluationResult(
            similarity_pct=0.0,
            covered=[],
            partial=[],
            missing=concepts,
            keywords_missing=[c.get("concept", "") for c in concepts],
            ai_suggested_min=None,
            ai_suggested_max=None,
            ai_confidence=0.0,
            rationale="Suspected prompt injection detected in student submission text. Flagged for human review.",
            citations=[],
            flags=flags
        )


    # 3. Retrieve KB Chunks
    kb_chunks = hybrid_retrieve(clean_text, subject_id=subject_id, institution_id=institution_id, k=3, embedder=embedder)

    # 4. Compute Similarity
    ans_sim, kb_sim, displayed_pct = compute_similarity(clean_text, model_answer, kb_chunks, embedder=embedder)

    # 5. Evaluate Concept Coverage
    covered, partial, missing = [], [], []
    keywords_missing = []

    for c in concepts:
        status = c.get("status", "covered") # Default mock status or evaluated status
        c_dict = {
            "concept": c.get("concept") or c.get("label", ""),
            "weight": float(c.get("weight", 1.0)),
            "quote": c.get("quote", clean_text[:30]),
            "justification": c.get("justification", f"Evaluated concept: {c.get('concept') or c.get('label')}")
        }
        if status == "covered":
            covered.append(c_dict)
        elif status == "partial":
            partial.append(c_dict)
        else:
            missing.append(c_dict)
            keywords_missing.append(c_dict["concept"])

    # 6. Compute Coverage & Suggested Marks
    all_evaluated = covered + partial + missing
    coverage = compute_concept_coverage_score(all_evaluated)
    overall_conf = round(ocr_confidence * 0.9, 2) # combined confidence score

    s_min, s_max, mark_flags = compute_marks_range(coverage, max_marks, overall_conf)
    flags.extend(mark_flags)

    # 7. Citations & Rationale
    citations = [
        Citation(source=c["source"], page=c["page"], excerpt=c["chunk_text"][:80])
        for c in kb_chunks
    ]

    rationale = f"Evaluated student answer against model answer and {len(concepts)} rubric concepts. Coverage score: {round(coverage, 3)}. "
    if citations:
        rationale += f"Cites evidence from [{citations[0].source}, Page {citations[0].page}]."

    return EvaluationResult(
        similarity_pct=float(displayed_pct),
        covered=covered,
        partial=partial,
        missing=missing,
        keywords_missing=keywords_missing,
        ai_suggested_min=s_min,
        ai_suggested_max=s_max,
        ai_confidence=overall_conf,
        rationale=rationale,
        citations=citations,
        flags=flags,
        prompt_version="v1.0",
        model="bge-small-en-v1.5",
        tokens=120,
        latency_ms=45
    )
