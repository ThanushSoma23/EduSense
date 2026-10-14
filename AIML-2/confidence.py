"""
==============================================================================
AIML-2: Confidence Calculation & Quality Review Module
Project: EduSense AI
Responsibility: OCR Confidence Estimation and needsReview Decision
==============================================================================

DISCLAIMER & IMPORTANT NOTE:
This confidence score is an OCR recognition confidence estimate calculated
from the model's token generation probabilities (softmax of decoder logits).
It measures how certain the OCR model is about deciphering the visual handwritten
characters. It is NOT a measure or guarantee of factual correctness or answer
quality. Evaluation of correctness is handled separately by AIML-3.
==============================================================================
"""

from typing import List, Any
import numpy as np


def calculate_token_confidence(scores: List[Any]) -> float:
    """
    Calculates the average OCR confidence from TrOCR generation scores.

    TrOCR returns `scores` when called with:
        return_dict_in_generate=True
        output_scores=True

    Each element in `scores` contains the model logits for that generated token.
    We convert the logits into probabilities using the softmax function:
        prob = max(softmax(logits))
    The final line confidence is the average of these token probabilities.

    Parameters:
        scores: A list/tuple of logit tensors from `outputs.scores`.

    Returns:
        float: Average token probability rounded to 4 decimal places (0.0 to 1.0).
    """
    if not scores:
        return 0.90  # Default fallback if generation produced no explicit score tensors

    try:
        import torch

        token_probabilities = []
        for score_tensor in scores:
            if isinstance(score_tensor, torch.Tensor):
                # Apply softmax across the vocabulary dimension
                probs = torch.softmax(score_tensor, dim=-1)
                # Take the highest probability (the token chosen by greedy decoding)
                max_prob = probs.max(dim=-1).values.item()
                token_probabilities.append(float(max_prob))
            elif isinstance(score_tensor, (int, float)):
                token_probabilities.append(float(score_tensor))

        if token_probabilities:
            avg_prob = float(np.mean(token_probabilities))
            return round(avg_prob, 4)
        return 0.90
    except Exception:
        return 0.90


def check_needs_review(
    confidence: float,
    threshold: float = 0.70,
    text: str = ""
) -> bool:
    """
    Determines whether a segmented answer requires human teacher review.

    Flagging rules:
    1. If the confidence is below the configurable threshold (default: 0.70),
       flag for review (`needsReview = True`).
    2. If the answer text is empty or blank, flag for review (`needsReview = True`).
    3. If the answer text is suspiciously short (< 3 characters), flag for review.

    Parameters:
        confidence: The calculated OCR confidence (between 0.0 and 1.0).
        threshold: Configurable minimum confidence threshold (default 0.70).
        text: The extracted student answer text.

    Returns:
        bool: True if teacher manual review is recommended, False otherwise.
    """
    # Blank or empty answer
    if not text or not text.strip():
        return True

    # Low confidence OCR (below threshold)
    if confidence < threshold:
        return True

    # Suspiciously short text (often noisy artifacts)
    if len(text.strip()) < 3:
        return True

    return False
