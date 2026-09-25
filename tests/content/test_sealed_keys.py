"""Hidden-key modules must not expose answers outside the sealed blob."""

import json
from pathlib import Path

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


def test_d7_answers_are_sealed() -> None:
    """Every D7 exercise keeps its answer fields inside `sealed`."""
    files = sorted(LESSONS.glob("D7-*.json"))
    assert files, "no D7 lessons built"
    for path in files:
        for exercise in json.loads(path.read_text(encoding="utf-8"))["exercises"]:
            leaked = ANSWER_FIELDS & exercise.keys()
            assert not leaked, f"{exercise['id']} exposes {sorted(leaked)}"
            assert "sealed" in exercise, f"{exercise['id']} has no sealed key"
