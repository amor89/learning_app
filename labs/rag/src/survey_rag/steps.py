"""The seven pipeline steps you write in modules B21 and B22.

Each function raises NotImplementedError until you fill it in. The tests in
tests/test_steps.py say exactly what each one must do.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

REFUSAL = "I cannot answer from the sources."


def chunk_words(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping windows of words (lesson B21-L1).

    Args:
        text: The section text.
        size: Words per window.
        overlap: Words shared by neighbouring windows.

    Returns:
        Windows in order. The last may be shorter than size.

    Raises:
        ValueError: If size is not positive or overlap is not in [0, size).
    """
    raise NotImplementedError("chunk_words")


def top_k(query_vec: NDArray[np.float64], chunk_vecs: NDArray[np.float64], k: int) -> list[int]:
    """Row indices of the k chunks most similar to the query, best first (lesson B21-L2).

    Args:
        query_vec: The question's vector.
        chunk_vecs: One vector per row.
        k: How many to return.

    Returns:
        Indices ordered by cosine similarity, highest first, ties by row order.

    Raises:
        ValueError: If the query vector has zero length.
    """
    raise NotImplementedError("top_k")


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Fuse rankings of IDs with reciprocal rank fusion (lesson B21-L2).

    Args:
        rankings: Each list holds IDs, best first.
        k: The RRF constant.

    Returns:
        IDs by fused score, highest first. Ties go to the smaller ID.
    """
    raise NotImplementedError("rrf")


def build_context(chunks: list[tuple[str, str]], budget_words: int) -> str:
    """Tagged sources in rank order, stopping before the budget overflows (lesson B21-L3).

    Args:
        chunks: (chunk_id, text) pairs, best first.
        budget_words: Most words of chunk text to include.

    Returns:
        One <source id="..."> element per line. Empty when nothing fits.
    """
    raise NotImplementedError("build_context")


def check_citations(answer: str, supplied_ids: set[str]) -> list[str]:
    """Problems with an answer's citations, empty when there are none (lesson B21-L3).

    Args:
        answer: The model's reply.
        supplied_ids: IDs of the chunks sent in the prompt.

    Returns:
        "unknown:<id>" for each invented ID, sorted, then "no_citation" when
        nothing is cited and the answer is not REFUSAL.
    """
    raise NotImplementedError("check_citations")


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Share of the relevant IDs found in the first k of a ranking (lesson B22-L1).

    Args:
        ranked: Retrieved IDs, best first.
        relevant: IDs a person marked as answering the question.
        k: Cut-off.

    Returns:
        A value from 0 to 1.

    Raises:
        ValueError: If relevant is empty or k is below 1.
    """
    raise NotImplementedError("recall_at_k")


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    """1 / rank of the first relevant ID, counting from 1, or 0.0 if none (lesson B22-L1).

    Args:
        ranked: Retrieved IDs, best first.
        relevant: IDs a person marked as answering the question.

    Returns:
        A value from 0 to 1.
    """
    raise NotImplementedError("reciprocal_rank")
