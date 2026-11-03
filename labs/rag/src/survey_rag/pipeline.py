"""Answer one question: retrieve, build the prompt, call the model, check citations."""

from __future__ import annotations

from dataclasses import dataclass

from survey_rag.index import Index
from survey_rag.llm import CallModel
from survey_rag.prompt import build_messages
from survey_rag.steps import check_citations


@dataclass(frozen=True)
class Answer:
    """One answered question. Grain: one question in one run."""

    question: str
    text: str
    sources: list[str]
    problems: list[str]


def answer_question(
    question: str, index: Index, call_model: CallModel, k: int = 5, budget_words: int = 300
) -> Answer:
    """Retrieve, prompt, call and check.

    Args:
        question: The user's question.
        index: Search over the notes.
        call_model: Function from messages to reply text.
        k: Most chunks to consider.
        budget_words: Most words of source text in the prompt.

    Returns:
        The answer, the sources sent and any citation problems.
    """
    ranked = index.search(question)[:k]
    messages, supplied = build_messages(question, ranked, budget_words)
    text = call_model(messages)
    return Answer(question, text, sorted(supplied), check_citations(text, supplied))
