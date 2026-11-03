"""Reference solutions for src/survey_rag/steps.py.

Read this only after your own version passes the tests. The repository's CI
copies this file over the stubs and runs the lab's tests, so it stays correct.
"""

from __future__ import annotations

import re

import numpy as np
from numpy.typing import NDArray

REFUSAL = "I cannot answer from the sources."
CITATION = re.compile(r"\[([^\]]+)\]")


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
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(f"need size > 0 and 0 <= overlap < size, got {size}, {overlap}")
    words = text.split()
    if not words:
        return []
    step = size - overlap
    return [" ".join(words[i : i + size]) for i in range(0, max(len(words) - overlap, 1), step)]


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
    q_len = np.linalg.norm(query_vec)
    if q_len == 0:
        raise ValueError("query vector has zero length")
    row_len = np.linalg.norm(chunk_vecs, axis=1)
    safe_len = np.where(row_len == 0, 1.0, row_len)
    scores = (chunk_vecs @ query_vec) / (safe_len * q_len)
    return [int(i) for i in np.argsort(-scores, kind="stable")[:k]]


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Fuse rankings of IDs with reciprocal rank fusion (lesson B21-L2).

    Args:
        rankings: Each list holds IDs, best first.
        k: The RRF constant.

    Returns:
        IDs by fused score, highest first. Ties go to the smaller ID.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1 / (k + rank)
    return sorted(scores, key=lambda item: (-scores[item], item))


def build_context(chunks: list[tuple[str, str]], budget_words: int) -> str:
    """Tagged sources in rank order, stopping before the budget overflows (lesson B21-L3).

    Args:
        chunks: (chunk_id, text) pairs, best first.
        budget_words: Most words of chunk text to include.

    Returns:
        One <source id="..."> element per line. Empty when nothing fits.
    """
    parts: list[str] = []
    used = 0
    for chunk_id, text in chunks:
        clean = text.replace("</source>", "")
        n_words = len(clean.split())
        if used + n_words > budget_words:
            break
        parts.append(f'<source id="{chunk_id}">{clean}</source>')
        used += n_words
    return "\n".join(parts)


def check_citations(answer: str, supplied_ids: set[str]) -> list[str]:
    """Problems with an answer's citations, empty when there are none (lesson B21-L3).

    Args:
        answer: The model's reply.
        supplied_ids: IDs of the chunks sent in the prompt.

    Returns:
        "unknown:<id>" for each invented ID, sorted, then "no_citation" when
        nothing is cited and the answer is not REFUSAL.
    """
    cited = set(CITATION.findall(answer))
    problems = [f"unknown:{cid}" for cid in sorted(cited - supplied_ids)]
    if not cited and answer.strip() != REFUSAL:
        problems.append("no_citation")
    return problems


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
    if not relevant:
        raise ValueError("relevant is empty: the question has no gold answer")
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    """1 / rank of the first relevant ID, counting from 1, or 0.0 if none (lesson B22-L1).

    Args:
        ranked: Retrieved IDs, best first.
        relevant: IDs a person marked as answering the question.

    Returns:
        A value from 0 to 1.
    """
    for rank, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1 / rank
    return 0.0
