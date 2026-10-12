import math
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def compute_suggested_marks_range(
    concepts: List[Dict[str, Any]],
    max_marks: float,
    confidence: float
) -> Tuple[float, float]:
    """
    Deterministic, documented formula for suggested marks range (never LLM-generated):
    1. coverage_score = (count(covered) + 0.5 * count(partial)) / total_concepts
    2. center = coverage_score * max_marks
    3. band_half_width = ceil((1 - confidence) * max_marks * 0.5 * 10) / 10
    4. min_marks = max(0.0, center - band_half_width)
    5. max_marks = min(max_marks, center + band_half_width)
    """
    if not concepts:
        return (0.0, round(max_marks, 1))

    total = len(concepts)
    covered_count = sum(1 for c in concepts if c.get("status") == "covered")
    partial_count = sum(1 for c in concepts if c.get("status") == "partial")

    coverage_score = (covered_count + (0.5 * partial_count)) / float(total)
    center = coverage_score * max_marks

    # Clamp confidence between 0.1 and 1.0
    conf = max(0.1, min(1.0, float(confidence)))
    band = math.ceil((1.0 - conf) * max_marks * 0.5 * 10) / 10.0

    suggested_min = round(max(0.0, center - band), 1)
    suggested_max = round(min(max_marks, center + band), 1)

    # Ensure min <= max
    if suggested_min > suggested_max:
        suggested_min = suggested_max

    return (suggested_min, suggested_max)
