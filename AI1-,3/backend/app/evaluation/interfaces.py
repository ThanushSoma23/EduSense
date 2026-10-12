import math
import uuid
import logging
from typing import List, Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseEmbedder:
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

class MockEmbedder(BaseEmbedder):
    """Deterministic mock embedder (384-dimensional vector based on text hash/length)."""
    def embed(self, text: str) -> List[float]:
        if not text:
            return [0.0] * 384
        val = sum(ord(c) for c in text) % 1000 / 1000.0
        vec = [math.sin(val + i) for i in range(384)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

class BaseLLM:
    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        raise NotImplementedError

class MockLLM(BaseLLM):
    """Deterministic mock LLM for structured output."""
    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        # Simple mock response generation
        if "ConceptCoverageResponse" in response_model.__name__:
            verdicts = [
                {"concept": "Handshake sequence", "status": "covered", "quote": "three-way handshake", "justification": "Directly mentions handshake sequence.", "weight": 0.30},
                {"concept": "SYN packet", "status": "covered", "quote": "SYN packet sent", "justification": "Mentions SYN packet.", "weight": 0.20},
                {"concept": "ACK packet", "status": "covered", "quote": "ACK returned", "justification": "Mentions ACK packet.", "weight": 0.20},
                {"concept": "Sequence-number sync", "status": "partial", "quote": "seq number initialised", "justification": "Mentions seq number initialisation partially.", "weight": 0.15},
                {"concept": "Reliable communication", "status": "missing", "quote": None, "justification": "No mention of reliable communication guarantees.", "weight": 0.15},
            ]
            return response_model(verdicts=verdicts, rationale="Evaluated concept presence across student response.") # type: ignore
        return response_model()

class BaseVectorStore:
    def upsert(self, chunks: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def search(self, embedding: List[float], institution_id: str, subject_id: str, k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

class MockVectorStore(BaseVectorStore):
    """In-memory vector store for testing with tenant isolation."""
    def __init__(self):
        self.store: List[Dict[str, Any]] = []

    def upsert(self, chunks: List[Dict[str, Any]]) -> None:
        for chunk in chunks:
            chunk_id = chunk.get("id") or str(uuid.uuid4())
            chunk["id"] = chunk_id
            self.store.append(chunk)

    def search(self, embedding: List[float], institution_id: str, subject_id: str, k: int = 5) -> List[Dict[str, Any]]:
        # Filter by tenant & subject
        filtered = [
            c for c in self.store
            if c.get("institution_id") == institution_id and c.get("subject_id") == subject_id
        ]
        if not filtered:
            return []

        def cos_sim(v1, v2):
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            n1 = math.sqrt(sum(a * a for a in v1))
            n2 = math.sqrt(sum(b * b for b in v2))
            return dot / (n1 * n2) if (n1 and n2) else 0.0

        scored = [(c, cos_sim(embedding, c.get("embedding", []))) for c in filtered]
        scored.sort(key=lambda x: x[1], reverse=True)
        res = []
        for item, score in scored[:k]:
            item_copy = dict(item)
            item_copy["score"] = score
            res.append(item_copy)
        return res

# Global instance for mock DB vector store
mock_vector_store = MockVectorStore()
