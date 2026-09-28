import logging
import math
import re
from typing import List

logger = logging.getLogger(__name__)

_model_cache = None

def get_embedding_model():
    global _model_cache
    if _model_cache is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformers (all-MiniLM-L6-v2)...")
            _model_cache = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"SentenceTransformer load skipped or failed ({e}). Using word-overlap fallback.")
            _model_cache = "fallback"
    return _model_cache

def compute_cosine_similarity(text1: str, text2: str) -> float:
    if not text1.strip() or not text2.strip():
        return 0.0

    model = get_embedding_model()
    if model != "fallback":
        try:
            embeddings = model.encode([text1, text2])
            vec1, vec2 = embeddings[0], embeddings[1]
            dot = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(b * b for b in vec2))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            similarity = dot / (norm1 * norm2)
            return round(max(0.0, min(1.0, float(similarity))) * 100, 2)
        except Exception as e:
            logger.error(f"SentenceTransformer encoding error: {e}. Falling back to token overlap.")

    # Word-level Jaccard token overlap fallback
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))
    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)
    sim = len(intersection) / float(len(union))
    return round(sim * 100, 2)
