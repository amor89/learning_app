"""Quality gates for the interview practice bank in content/interview/.

For each from-scratch task:
- the reference solution passes its checker,
- the starter code fails,
- every seeded bug fails,
- every listed wrong answer fails on the rule it names,
- the solution uses only names a lesson or the task's primer explains.

For the theory bank:
- every topic has questions, and every item names lessons that exist (the loader),
- multiple-choice options are unique and open questions have distinct points,
- time limits leave room to read the question.
"""

from __future__ import annotations

import pytest

from checkers import check_python
from learnkit.loader import load_course, load_interview
from learnkit.models import InterviewTask, TheoryQuestion, word_count
from learnkit.taught import untaught_tasks

COURSE = load_course()
INTERVIEW = load_interview(COURSE)
TASKS = INTERVIEW.tasks
QUESTIONS = INTERVIEW.all_questions()
SECONDS_PER_WORD = 0.5


def checker_dict(task: InterviewTask) -> dict[str, object]:
    """The checker exactly as the browser receives it."""
    return task.checker.model_dump(mode="json")


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_solution_passes(task: InterviewTask) -> None:
    result = check_python(checker_dict(task), task.solution)
    assert result.passed, f"{task.id} solution failed: {result.rule_id} {result.feedback}"


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_starter_fails(task: InterviewTask) -> None:
    assert not check_python(checker_dict(task), task.starter).passed


@pytest.mark.parametrize(
    ("task", "index"),
    [(task, i) for task in TASKS for i in range(len(task.seeded_bugs))],
    ids=lambda v: v.id if hasattr(v, "id") else str(v),
)
def test_seeded_bug_fails(task: InterviewTask, index: int) -> None:
    result = check_python(checker_dict(task), task.seeded_bugs[index])
    assert not result.passed, f"{task.id} seeded bug {index} passed the checker"


@pytest.mark.parametrize(
    ("task", "index"),
    [(task, i) for task in TASKS for i in range(len(task.wrong_answers))],
    ids=lambda v: v.id if hasattr(v, "id") else str(v),
)
def test_wrong_answer_triggers_feedback(task: InterviewTask, index: int) -> None:
    wrong = task.wrong_answers[index]
    result = check_python(checker_dict(task), wrong.answer)
    assert not result.passed
    assert result.rule_id == wrong.triggers, (
        f"{task.id} wrong answer {index} hit {result.rule_id}, expected {wrong.triggers}"
    )


def test_task_solutions_use_only_taught_names() -> None:
    """A task may use a name only when a lesson or its primer explains it."""
    gaps = untaught_tasks(INTERVIEW, COURSE)
    report = "\n".join(f"{task_id}: {', '.join(names)}" for task_id, names in gaps.items())
    assert not gaps, f"Untaught names. Explain them in the task's primer:\n{report}"


def test_question_ids_are_unique() -> None:
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q.id)
def test_question_is_well_formed(question: TheoryQuestion) -> None:
    if question.kind == "mcq":
        texts = [o.text for o in question.options]
        assert len(texts) == len(set(texts)), f"{question.id}: repeated option text"
        assert len({o.id for o in question.options}) == len(texts)
    else:
        assert len(question.points) == len(set(question.points)), f"{question.id}: repeated point"
    reading = word_count(question.question) * SECONDS_PER_WORD
    assert question.seconds >= reading + 15, f"{question.id}: too little time to read and answer"


def test_answer_positions_vary() -> None:
    """Multiple-choice keys are not always the same option position."""
    positions = [
        [o.id for o in q.options].index(q.answer or "") for q in QUESTIONS if q.kind == "mcq"
    ]
    assert len(set(positions)) > 1 or len(positions) < 3
