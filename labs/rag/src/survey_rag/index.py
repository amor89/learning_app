"""Rank chunks for a question with two keyword rankings fused by RRF.

Both rankings are TF-IDF: one on words, which matches exact terms such as W14,
and one on character n-grams, which tolerates spelling variants. Neither knows
meaning. Swap in sentence embeddings (lesson B15-L1) for a semantic ranking:
any function from texts to a 2-D array of vectors works with top_k.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer

from survey_rag.corpus import Chunk
from survey_rag.steps import rrf, top_k


class Index:
    """Search over a fixed list of chunks."""

    def __init__(self, chunks: list[Chunk]) -> None:
        """Fit both vectorisers on the chunk texts.

        Args:
            chunks: The chunks to search. The list must not be empty.

        Raises:
            ValueError: If chunks is empty.
        """
        if not chunks:
            raise ValueError("cannot index an empty list of chunks")
        self.chunks = chunks
        self._by_id = {c.chunk_id: c for c in chunks}
        texts = [f"{c.heading}. {c.text}" for c in chunks]
        self._vectorisers = [
            TfidfVectorizer(),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)),
        ]
        self._matrices: list[NDArray[np.float64]] = [
            np.asarray(v.fit_transform(texts).toarray(), dtype=np.float64)
            for v in self._vectorisers
        ]

    def search(self, question: str, doc_ids: set[str] | None = None) -> list[Chunk]:
        """All allowed chunks, best first.

        Args:
            question: The user's question.
            doc_ids: Keep only chunks from these documents. None keeps all.

        Returns:
            Chunks ranked by RRF over the two rankings. Empty when no chunk is
            allowed or the question shares no term with the notes.
        """
        allowed = [i for i, c in enumerate(self.chunks) if doc_ids is None or c.doc_id in doc_ids]
        if not allowed:
            return []
        rankings: list[list[str]] = []
        for vectoriser, matrix in zip(self._vectorisers, self._matrices, strict=True):
            query = np.asarray(vectoriser.transform([question]).toarray()[0], dtype=np.float64)
            if not query.any():
                continue
            order = top_k(query, matrix[allowed], len(allowed))
            rankings.append([self.chunks[allowed[i]].chunk_id for i in order])
        return [self._by_id[cid] for cid in rrf(rankings)]
