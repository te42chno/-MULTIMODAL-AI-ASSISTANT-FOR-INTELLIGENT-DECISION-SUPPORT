import json
import logging
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

try:
    import numpy as np
except ImportError:  # Vercel serverless runtime
    np = None

from app.models.db_models import DocumentChunk, EvidenceChunk, FileRecord
from app.schemas.chat import Citation
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def _cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    if np is not None:
        return float(np.dot(np.asarray(a, dtype="float32"), np.asarray(b, dtype="float32")))
    return sum(x * y for x, y in zip(a, b))


class VectorRepository:
    """Hybrid (dense + lexical) retrieval over unified multimodal evidence chunks."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def add_document_chunks(self, file_id: str, chunks: List[Dict[str, Any]]):
        """Backward-compatible document indexing; also mirrors chunks into the evidence index."""
        texts = [c["text"] for c in chunks]
        embeddings = embedding_service.embed_texts(texts)

        rows = []
        for i, c in enumerate(chunks):
            rows.append(
                DocumentChunk(
                    file_id=file_id,
                    chunk_index=c.get("chunk_index", i),
                    page_number=c.get("page_number", 1),
                    text=c["text"],
                    embedding_json=json.dumps(embeddings[i]),
                )
            )
        self.db.add_all(rows)
        self.db.commit()

        self.add_evidence_chunks(
            file_id,
            [
                {
                    "chunk_index": c.get("chunk_index", i),
                    "modality": "document",
                    "source_ref": f"Page {c.get('page_number', 1)}",
                    "text": c["text"],
                    "metadata": {"page_number": c.get("page_number", 1)},
                }
                for i, c in enumerate(chunks)
            ],
            embeddings=embeddings,
        )
        return rows

    def add_evidence_chunks(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ):
        """Index any modality as evidence. Chunk needs: text; optionally source_ref, modality, metadata."""
        if not chunks:
            return []
        texts = [c["text"] for c in chunks]
        vectors = embeddings or embedding_service.embed_texts(texts)

        rows = []
        for i, c in enumerate(chunks):
            rows.append(
                EvidenceChunk(
                    file_id=file_id,
                    chunk_index=c.get("chunk_index", i),
                    modality=c.get("modality", "document"),
                    source_ref=c.get("source_ref", ""),
                    text=c["text"],
                    embedding_json=json.dumps(vectors[i]),
                    metadata_json=json.dumps(c.get("metadata", {})),
                )
            )
        self.db.add_all(rows)
        self.db.commit()
        return rows

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def search_evidence(
        self,
        query: str,
        file_ids: Optional[List[str]] = None,
        top_k: int = 5,
        score_threshold: float = 0.08,
        modality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = self.db.query(EvidenceChunk, FileRecord).join(
            FileRecord, EvidenceChunk.file_id == FileRecord.id
        )
        if file_ids:
            q = q.filter(EvidenceChunk.file_id.in_(file_ids))
        if modality:
            q = q.filter(EvidenceChunk.modality == modality)
        rows = q.all()
        if not rows:
            return []

        query_vec = embedding_service.embed_query(query)
        q_tokens = set(_tokens(query))
        doc_freq: Counter = Counter()
        texts = []
        for chunk, _ in rows:
            toks = set(_tokens(chunk.text))
            texts.append(toks)
            doc_freq.update(toks)

        n_docs = max(len(rows), 1)
        scored = []
        for (chunk, file_rec), toks in zip(rows, texts):
            dense = _cosine(query_vec, json.loads(chunk.embedding_json or "[]"))
            meta = json.loads(chunk.metadata_json or "{}")

            # Lightweight BM25-style lexical score using IDF weights.
            overlap = 0.0
            for term in q_tokens:
                if term in toks:
                    idf = math.log(1 + n_docs / (1 + doc_freq[term]))
                    overlap += idf
            lexical = overlap / max(sum(math.log(1 + n_docs / (1 + doc_freq[t])) for t in q_tokens), 1e-9)

            score = 0.75 * max(dense, 0.0) + 0.25 * lexical
            if score >= score_threshold:
                scored.append(
                    {
                        "chunk_id": chunk.id,
                        "file_id": chunk.file_id,
                        "filename": file_rec.filename,
                        "page_number": meta.get("page_number") if isinstance(meta.get("page_number"), int) else None,
                        "source_ref": chunk.source_ref,
                        "modality": chunk.modality,
                        "text": chunk.text,
                        "score": round(score, 4),
                        "metadata": meta,
                    }
                )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def search_similar_chunks(
        self,
        query: str,
        file_ids: Optional[List[str]] = None,
        top_k: int = 4,
        score_threshold: float = 0.15,
    ) -> List[Dict[str, Any]]:
        results = self.search_evidence(
            query,
            file_ids=file_ids,
            top_k=top_k,
            score_threshold=min(score_threshold, 0.08),
        )
        if results:
            return results

        # Legacy fallback for records indexed before the evidence table existed.
        query_vec = embedding_service.embed_query(query)
        q_tokens = set(_tokens(query))
        scored = []
        rows = (
            self.db.query(DocumentChunk, FileRecord)
            .join(FileRecord, DocumentChunk.file_id == FileRecord.id)
            .all()
        )
        for chunk, file_rec in rows:
            if not chunk.embedding_json:
                continue
            vec = json.loads(chunk.embedding_json)
            dense = _cosine(query_vec, vec)
            chunk_tokens = set(_tokens(chunk.text))
            lexical = len(q_tokens & chunk_tokens) / max(len(q_tokens), 1)
            score = 0.75 * max(dense, 0.0) + 0.25 * lexical
            if score >= score_threshold:
                scored.append(
                    {
                        "chunk_id": chunk.id,
                        "file_id": chunk.file_id,
                        "filename": file_rec.filename,
                        "page_number": chunk.page_number,
                        "source_ref": f"Page {chunk.page_number}",
                        "modality": "document",
                        "text": chunk.text,
                        "score": round(score, 4),
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Citations
    # ------------------------------------------------------------------
    def build_citations(self, chunk_results: List[Dict[str, Any]]) -> List[Citation]:
        citations = []
        for c in chunk_results:
            snippet = c["text"][:220].strip() + ("..." if len(c["text"]) > 220 else "")
            source_ref = c.get("source_ref") or (
                f"Page {c['page_number']}" if c.get("page_number") else ""
            )
            citations.append(
                Citation(
                    source_id=c["chunk_id"],
                    filename=c["filename"],
                    page_number=c.get("page_number") if isinstance(c.get("page_number"), int) else None,
                    row_or_item=source_ref or None,
                    snippet=snippet,
                    relevance_score=c["score"],
                )
            )
        return citations
