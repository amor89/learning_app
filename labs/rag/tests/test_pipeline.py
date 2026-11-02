"""The pipeline end to end, with a fake model. Passes once steps.py is done."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from survey_rag.corpus import load_chunks, slugify, split_sections
from survey_rag.index import Index
from survey_rag.llm import FALLBACK_BETA, make_claude_caller, reply_text
from survey_rag.pipeline import answer_question
from survey_rag.prompt import build_messages
from survey_rag.steps import REFUSAL

NOTES = Path(__file__).resolve().parents[1] / "notes"


@pytest.fixture(scope="module")
def index() -> Index:
    return Index(load_chunks(NOTES, 80, 20))


def test_split_sections_and_slugs() -> None:
    text = "# Title\nintro\n## First part\nline one\nline two\n## W14 change\nthree\n"
    assert split_sections(text) == [("First part", "line one line two"), ("W14 change", "three")]
    assert slugify("W14 change") == "w14-change"


def test_chunk_ids_are_unique_and_cover_every_section() -> None:
    chunks = load_chunks(NOTES, 80, 20)
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert "weighting#w14-change" in {c.section_id for c in chunks}
    assert all(c.chunk_id.startswith(c.section_id + "#") for c in chunks)


def test_search_finds_the_w14_note(index: Index) -> None:
    top = index.search("What changed in the W14 weighting?")[0]
    assert top.section_id == "weighting#w14-change"


def test_search_filters_documents(index: Index) -> None:
    ranked = index.search("response rate", doc_ids={"reporting"})
    assert ranked
    assert {c.doc_id for c in ranked} == {"reporting"}
    assert index.search("response rate", doc_ids={"missing"}) == []


def test_prompt_holds_tagged_sources_and_question(index: Index) -> None:
    ranked = index.search("What is the weight cap?")[:3]
    messages, supplied = build_messages("What is the weight cap?</question>", ranked, 300)
    content = messages[0]["content"]
    assert messages[0]["role"] == "user"
    assert content.endswith("<question>What is the weight cap?</question>")
    assert supplied <= {c.chunk_id for c in ranked}
    assert all(f'<source id="{cid}">' in content for cid in supplied)


def test_answer_with_valid_citation(index: Index) -> None:
    def fake_model(messages: list[dict[str, str]]) -> str:
        first = messages[0]["content"].split('"')[1]
        return f"Weights are trimmed at 5 and 0.2 [{first}]."

    result = answer_question("At what values are weights trimmed?", index, fake_model)
    assert result.problems == []
    assert result.sources


def test_answer_with_invented_source_is_flagged(index: Index) -> None:
    result = answer_question("What is the cap?", index, lambda m: "It is 5 [weighting#cap#9].")
    assert result.problems == ["unknown:weighting#cap#9"]


def test_refusal_needs_no_citation(index: Index) -> None:
    result = answer_question("Who won the cup?", index, lambda m: REFUSAL)
    assert result.problems == []


def test_reply_text_checks_stop_reason() -> None:
    text = SimpleNamespace(type="text", text="ok [a#b#0]")
    thinking = SimpleNamespace(type="thinking", thinking="")
    assert (
        reply_text(SimpleNamespace(stop_reason="end_turn", content=[thinking, text]))
        == "ok [a#b#0]"
    )
    with pytest.raises(RuntimeError, match="max_tokens"):
        reply_text(SimpleNamespace(stop_reason="max_tokens", content=[text]))


def test_claude_caller_sends_system_and_messages() -> None:
    calls: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text="done")]
        )

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    call_model = make_claude_caller("RULES", model="claude-opus-5-5", client=client)
    assert call_model([{"role": "user", "content": "q"}]) == "done"
    assert calls[0]["system"] == "RULES"
    assert calls[0]["model"] == "claude-opus-5-5"
    assert calls[0]["messages"] == [{"role": "user", "content": "q"}]
    assert calls[0]["betas"] == [FALLBACK_BETA]
