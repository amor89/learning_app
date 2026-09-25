"""Quality gates for every exercise checked by Python.

For each code exercise with a Python checker:
- the reference solution passes,
- the starter code fails,
- every seeded bug fails,
- every listed wrong answer fails on the rule it names.

For each spot-the-bug exercise with a Python fix checker:
- the fix solution passes,
- the original buggy code fails,
- every extra seeded bug fails.
"""

from __future__ import annotations

import pytest

from checkers import check_python
from learnkit.loader import load_course
from learnkit.models import CodeExercise, PythonChecker, SpotBugExercise

COURSE = load_course()
EXERCISES = [ex for lesson in COURSE.lessons() for ex in lesson.exercises]

CODE = [
    ex for ex in EXERCISES if isinstance(ex, CodeExercise) and isinstance(ex.checker, PythonChecker)
]
FIXES = [
    ex
    for ex in EXERCISES
    if isinstance(ex, SpotBugExercise) and isinstance(ex.fix_checker, PythonChecker)
]


def checker_dict(checker: PythonChecker) -> dict[str, object]:
    """The checker exactly as the browser receives it."""
    return checker.model_dump(mode="json")


@pytest.mark.parametrize("ex", CODE, ids=lambda e: e.id)
def test_solution_passes(ex: CodeExercise) -> None:
    assert isinstance(ex.checker, PythonChecker)
    result = check_python(checker_dict(ex.checker), ex.solution)
    assert result.passed, f"{ex.id} solution failed: {result.rule_id} {result.feedback}"


@pytest.mark.parametrize("ex", CODE, ids=lambda e: e.id)
def test_starter_fails(ex: CodeExercise) -> None:
    assert isinstance(ex.checker, PythonChecker)
    if ex.starter:
        assert not check_python(checker_dict(ex.checker), ex.starter).passed


@pytest.mark.parametrize(
    ("ex", "index"),
    [(ex, i) for ex in CODE for i in range(len(ex.seeded_bugs))],
    ids=lambda v: v.id if hasattr(v, "id") else str(v),
)
def test_seeded_bug_fails(ex: CodeExercise, index: int) -> None:
    assert isinstance(ex.checker, PythonChecker)
    result = check_python(checker_dict(ex.checker), ex.seeded_bugs[index])
    assert not result.passed, f"{ex.id} seeded bug {index} passed the checker"


@pytest.mark.parametrize(
    ("ex", "index"),
    [(ex, i) for ex in CODE for i in range(len(ex.wrong_answers))],
    ids=lambda v: v.id if hasattr(v, "id") else str(v),
)
def test_wrong_answer_triggers_feedback(ex: CodeExercise, index: int) -> None:
    assert isinstance(ex.checker, PythonChecker)
    wrong = ex.wrong_answers[index]
    result = check_python(checker_dict(ex.checker), wrong.answer)
    assert not result.passed
    assert result.rule_id == wrong.triggers, (
        f"{ex.id} wrong answer {index} hit {result.rule_id}, expected {wrong.triggers}"
    )


@pytest.mark.parametrize("ex", FIXES, ids=lambda e: e.id)
def test_fix_solution_passes(ex: SpotBugExercise) -> None:
    assert isinstance(ex.fix_checker, PythonChecker)
    result = check_python(checker_dict(ex.fix_checker), ex.fix_solution)
    assert result.passed, f"{ex.id} fix failed: {result.rule_id} {result.feedback}"


@pytest.mark.parametrize("ex", FIXES, ids=lambda e: e.id)
def test_buggy_code_fails_fix_checker(ex: SpotBugExercise) -> None:
    assert isinstance(ex.fix_checker, PythonChecker)
    for code in [ex.code, *ex.fix_seeded_bugs]:
        assert not check_python(checker_dict(ex.fix_checker), code).passed
