"""Hidden-key modules must not expose answers outside the sealed blob."""

import json
from pathlib import Path

import pytest

LESSONS = Path(__file__).resolve().parents[2] / "site" / "content" / "lessons"
ANSWER_FIELDS = {
    "answer",
    "reason_answer",
    "bug_lines",
    "solution",
    "fix_solution",
    "explanation",
    "explanation_html",
    "wrong_answers",
    "gaps",
    "model_answer",
    "model_answer_html",
    "solution_lines",
    "fix_solution_lines",
}


@pytest.mark.parametrize("module", ["D7", "X3"])
def test_hidden_key_answers_are_sealed(module: str) -> None:
    """Every exercise in a hidden-key module keeps its answer fields inside `sealed`."""
    files = sorted(LESSONS.glob(f"{module}-*.json"))
    assert files, f"no {module} lessons built"
    for path in files:
        for exercise in json.loads(path.read_text(encoding="utf-8"))["exercises"]:
            leaked = ANSWER_FIELDS & exercise.keys()
            assert not leaked, f"{exercise['id']} exposes {sorted(leaked)}"
            assert "sealed" in exercise, f"{exercise['id']} has no sealed key"
