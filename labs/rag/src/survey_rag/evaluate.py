"""Score retrieval on the gold questions (lesson B22-L1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from survey_rag.index import Index
from survey_rag.steps import recall_at_k, reciprocal_rank


@dataclass(frozen=True)
class GoldQuestion:
    """A question and the section IDs a person marked as answering it."""

    question: str
    relevant: frozenset[str]


def load_gold(path: Path) -> list[GoldQuestion]:
    """Read a JSON Lines file of {"question": ..., "relevant": [...]}.

    Raises:
        ValueError: If a line has no relevant sections.
    """
    gold: list[GoldQuestion] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not row["relevant"]:
            raise ValueError(f"{path}:{n}: no relevant sections")
        gold.append(GoldQuestion(row["question"], frozenset(row["relevant"])))
    return gold


def section_ranking(index: Index, question: str) -> list[str]:
    """Section IDs in the order their first chunk is retrieved."""
    return list(dict.fromkeys(c.section_id for c in index.search(question)))


def evaluate_retrieval(index: Index, gold: list[GoldQuestion], k: int) -> dict[str, float]:
    """Mean recall at k and mean reciprocal rank over the gold questions.

    Raises:
        ValueError: If gold is empty.
    """
    if not gold:
        raise ValueError("no gold questions")
    recalls: list[float] = []
    ranks: list[float] = []
    for item in gold:
        ranked = section_ranking(index, item.question)
        recalls.append(recall_at_k(ranked, set(item.relevant), k))
        ranks.append(reciprocal_rank(ranked, set(item.relevant)))
    return {
        "n_questions": float(len(gold)),
        f"recall_at_{k}": sum(recalls) / len(recalls),
        "mrr": sum(ranks) / len(ranks),
    }
