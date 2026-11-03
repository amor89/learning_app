"""Retrieval quality on the gold questions. Passes once steps.py is done."""

from __future__ import annotations

from pathlib import Path

from survey_rag.corpus import load_chunks
from survey_rag.evaluate import evaluate_retrieval, load_gold
from survey_rag.index import Index

LAB = Path(__file__).resolve().parents[1]


def test_retrieval_meets_the_bar() -> None:
    index = Index(load_chunks(LAB / "notes", 80, 20))
    gold = load_gold(LAB / "eval" / "questions.jsonl")
    scores = evaluate_retrieval(index, gold, k=3)
    assert scores["n_questions"] == 12
    assert scores["recall_at_3"] >= 0.9, scores
    assert scores["mrr"] >= 0.8, scores
