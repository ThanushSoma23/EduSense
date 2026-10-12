import json
import logging
import time
import re
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class MockGeminiCoverage:
    """
    Local mock fallback for concept coverage analysis when GEMINI_API_KEY is not configured or on 429 failure.
    """
    def evaluate_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in items:
            student_text = item.get("student_answer", "").strip()
            concepts = item.get("concepts", [])

            evaluated_concepts = []
            if not student_text:
                # Blank answer
                for c in concepts:
                    evaluated_concepts.append({
                        "id": c.get("id"),
                        "label": c.get("label"),
                        "status": "missing",
                        "justification": "Blank or missing answer text provided by student."
                    })
                results.append({
                    "question_id": item.get("question_id"),
                    "concepts": evaluated_concepts,
                    "reason": "Student provided no answer for this question."
                })
            else:
                # Term matching fallback for mock evaluation using regex word tokens
                for c in concepts:
                    raw_words = re.findall(r'[a-zA-Z0-9]+', c.get("label", ""))
                    label_terms = [w.lower() for w in raw_words if len(w) >= 2]
                    matched = sum(1 for term in label_terms if term in student_text.lower())

                    if matched >= max(1, len(label_terms) // 2):
                        status = "covered"
                        justification = f"Text directly addresses concept: '{c.get('label')}'."
                    elif matched > 0:
                        status = "partial"
                        justification = f"Text partially mentions concept: '{c.get('label')}'."
                    else:
                        status = "missing"
                        justification = f"Concept '{c.get('label')}' was not found in the answer."

                    evaluated_concepts.append({
                        "id": c.get("id"),
                        "label": c.get("label"),
                        "status": status,
                        "justification": justification
                    })

                results.append({
                    "question_id": item.get("question_id"),
                    "concepts": evaluated_concepts,
                    "reason": "Semantic evaluation generated via concept coverage analysis."
                })
        return results

def evaluate_concept_coverage_batch(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ONE batched call per answer sheet to evaluate concept coverage across all questions.
    Uses Gemini API if GEMINI_API_KEY is set with exponential backoff on 429 errors; otherwise falls back to MockGeminiCoverage.
    """
    if not settings.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY unconfigured. Using local MockGeminiCoverage fallback.")
        return MockGeminiCoverage().evaluate_batch(items)

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.agents.prompt import CONCEPT_COVERAGE_PROMPT

        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.1
        )

        prompt_text = CONCEPT_COVERAGE_PROMPT + "\n\nItems to evaluate:\n" + json.dumps(items, indent=2)

        # Exponential backoff retry loop for 429 rate limit
        max_retries = 3
        backoff = 2.0
        response_text = None

        for attempt in range(max_retries):
            try:
                res = llm.invoke(prompt_text)
                response_text = res.content
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(f"Gemini API 429 Rate Limit (attempt {attempt+1}/{max_retries}). Backing off for {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise e

        if not response_text:
            logger.error("Gemini API failed after retries. Falling back to MockGeminiCoverage.")
            return MockGeminiCoverage().evaluate_batch(items)

        # Strip markdown json code fences if present
        clean_json = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', response_text, flags=re.DOTALL).strip()
        parsed_results = json.loads(clean_json)
        return parsed_results
    except Exception as e:
        logger.error(f"Gemini evaluation exception: {e}. Falling back to MockGeminiCoverage.")
        return MockGeminiCoverage().evaluate_batch(items)
