"""Stable embeddings shared by every modality.

Local development keeps scikit-learn's HashingVectorizer exactly as before, so
retrieval results are unchanged. On Vercel the heavy ML wheels are not bundled,
so an equivalent pure-Python unigram+bigram hashing embedder is used instead.
"""

import hashlib
import logging
import math
import re
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.feature_extraction.text import HashingVectorizer

    _SKLEARN_AVAILABLE = True
except ImportError:  # Vercel serverless runtime
    np = None
    HashingVectorizer = None
    _SKLEARN_AVAILABLE = False

_TOKEN = re.compile(r"[a-z0-9]+")


class EmbeddingService:
    """Stable, stateless embeddings shared by documents, tables, images, audio and video."""

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.model = None
        self.dimension = 768
        self.hasher = None

        # HashingVectorizer is deterministic and never needs fitting. This keeps
        # query vectors and document vectors in the same space across restarts.
        if _SKLEARN_AVAILABLE:
            self.hasher = HashingVectorizer(
                n_features=self.dimension,
                alternate_sign=False,
                norm="l2",
                lowercase=True,
                ngram_range=(1, 2),
            )

        if self.provider == "local_transformers":
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
                sample_dim = len(self.model.encode(["probe"])[0])
                self.dimension = int(sample_dim)
                logger.info("Loaded embedding model: %s", settings.EMBEDDING_MODEL)
            except Exception as exc:
                logger.warning("Embedding model unavailable (%s); using hashing embeddings.", exc)
                self.model = None

    def _hash_embedding(self, text: str) -> List[float]:
        """Dependency-free fallback: MD5-based unigram+bigram hashing, L2 normalised."""
        vector = [0.0] * self.dimension
        tokens = _TOKEN.findall((text or "").lower())
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.md5(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        clean = [str(t) if t else "" for t in texts]

        if self.model is not None:
            try:
                if _SKLEARN_AVAILABLE:
                    vectors = np.asarray(
                        self.model.encode(clean, convert_to_numpy=True), dtype="float32"
                    )
                    return self._normalize_np(vectors).tolist()
                return [self._normalise(v) for v in self.model.encode(clean)]
            except Exception as exc:
                logger.warning("Transformer embedding failed (%s); using hashing fallback.", exc)

        if self.hasher is not None:
            vectors = self.hasher.transform(clean).toarray().astype("float32")
            return self._normalize_np(vectors).tolist()

        return [self._hash_embedding(text) for text in clean]

    def embed_query(self, query: str) -> List[float]:
        result = self.embed_texts([query])
        return result[0] if result else [0.0] * self.dimension

    @staticmethod
    def _normalize_np(vectors):
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    @staticmethod
    def _normalise(vector: List[float]) -> List[float]:
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


embedding_service = EmbeddingService()
