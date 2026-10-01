import uuid
import logging
from typing import List, Dict, Any, Optional
from app.evaluation.interfaces import BaseEmbedder, BaseVectorStore, MockEmbedder, mock_vector_store
from app.db.supabase import db

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size_tokens: int = 350, overlap_tokens: int = 50) -> List[Dict[str, Any]]:
    """Simple structure-aware text chunker (~300-500 tokens)."""
    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size_tokens - overlap_tokens
    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size_tokens]
        chunk_text_str = " ".join(chunk_words)
        chunks.append({
            "text": chunk_text_str,
            "heading": f"Section {i // step + 1}",
            "page": (i // 500) + 1
        })
    return chunks

def index_document(
    file_bytes: bytes,
    filename: str,
    subject_id: str,
    institution_id: str,
    embedder: Optional[BaseEmbedder] = None,
    vector_store: Optional[BaseVectorStore] = None
) -> Dict[str, Any]:
    """
    Extract text, chunk (~300-500 tokens), embed, and upsert into kb_chunks table & vector store.
    Institution + subject isolation enforced.
    """
    embedder = embedder or MockEmbedder()
    v_store = vector_store or mock_vector_store

    text_content = file_bytes.decode("utf-8", errors="ignore")
    chunks = chunk_text(text_content)

    doc_id = f"doc-{uuid.uuid4()}"
    indexed_chunks = []

    for idx, c in enumerate(chunks):
        chunk_id = f"chunk-{uuid.uuid4()}"
        emb = embedder.embed(c["text"])

        chunk_record = {
            "id": chunk_id,
            "doc_id": doc_id,
            "institution_id": institution_id,
            "subject_id": subject_id,
            "source": filename,
            "page": c["page"],
            "heading": c["heading"],
            "text": c["text"],
            "embedding": emb
        }

        # Store in DB dictionary / vector store
        if hasattr(db, "kb_chunks") and isinstance(db.kb_chunks, dict):
            db.kb_chunks[chunk_id] = chunk_record

        indexed_chunks.append(chunk_record)

    v_store.upsert(indexed_chunks)

    logger.info(f"Indexed {len(indexed_chunks)} chunks for document '{filename}' (Tenant: {institution_id}, Subject: {subject_id}).")
    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunks_indexed": len(indexed_chunks),
        "institution_id": institution_id,
        "subject_id": subject_id
    }

def hybrid_retrieve(
    query: str,
    subject_id: str,
    institution_id: str,
    k: int = 5,
    embedder: Optional[BaseEmbedder] = None,
    vector_store: Optional[BaseVectorStore] = None
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: dense vector search + full-text search fused with Reciprocal Rank Fusion (RRF).
    Enforces strict institution_id + subject_id isolation.
    """
    embedder = embedder or MockEmbedder()
    v_store = vector_store or mock_vector_store

    query_emb = embedder.embed(query)

    # 1. Dense vector search
    dense_results = v_store.search(query_emb, institution_id=institution_id, subject_id=subject_id, k=k*2)

    # 2. Text keyword match search (Full-text simulation)
    all_chunks = []
    if hasattr(db, "kb_chunks") and isinstance(db.kb_chunks, dict):
        all_chunks = list(db.kb_chunks.values())
    else:
        all_chunks = getattr(v_store, "store", [])

    tenant_chunks = [
        c for c in all_chunks
        if c.get("institution_id") == institution_id and c.get("subject_id") == subject_id
    ]

    query_words = set(query.lower().split())
    text_results = []
    for c in tenant_chunks:
        c_words = set(c.get("text", "").lower().split())
        match_count = len(query_words.intersection(c_words))
        if match_count > 0:
            text_results.append((c, match_count))

    text_results.sort(key=lambda x: x[1], reverse=True)
    text_ranked = [c for c, _ in text_results[:k*2]]

    # 3. Reciprocal Rank Fusion (RRF)
    rrf_scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict[str, Any]] = {}
    c_param = 60 # RRF constant

    for rank, item in enumerate(dense_results):
        cid = item["id"]
        chunk_map[cid] = item
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (c_param + rank + 1)

    for rank, item in enumerate(text_ranked):
        cid = item["id"]
        chunk_map[cid] = item
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (c_param + rank + 1)

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    final_chunks = []
    for cid, rrf_score in fused[:k]:
        item = chunk_map[cid]
        final_chunks.append({
            "chunk_text": item.get("text", ""),
            "source": item.get("source", "Reference Document"),
            "page": item.get("page", 1),
            "heading": item.get("heading", ""),
            "score": round(rrf_score, 4)
        })

    return final_chunks
