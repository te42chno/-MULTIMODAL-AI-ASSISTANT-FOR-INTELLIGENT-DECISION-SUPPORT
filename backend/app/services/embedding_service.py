import logging
from typing import List

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Stable, stateless embeddings shared by documents, tables, images, audio and video."""

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.model = None
        self.dimension = 768

        # HashingVectorizer is deterministic and never needs fitting. This keeps
        # query vectors and document vectors in the same space across restarts.
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

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        clean = [str(t) if t else "" for t in texts]

        if self.model is not None:
            try:
                vectors = np.asarray(self.model.encode(clean, convert_to_numpy=True), dtype="float32")
                return self._normalize(vectors).tolist()
            except Exception as exc:
                logger.warning("Transformer embedding failed (%s); using hashing fallback.", exc)

        vectors = self.hasher.transform(clean).toarray().astype("float32")
        return self._normalize(vectors).tolist()

    def embed_query(self, query: str) -> List[float]:
        result = self.embed_texts([query])
        return result[0] if result else [0.0] * self.dimension

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


embedding_service = EmbeddingService()
