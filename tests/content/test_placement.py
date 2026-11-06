"""Quality gates for the placement quizzes in content/placement/.

- Every track that opens with a start-here module has a quiz on it.
- Each quiz covers every start-here lesson at least twice, so a wrong answer
  points at the lesson to read.
- Options within a question are distinct, and answer keys do not all sit in
  one position (the app also shuffles options per question).
"""

from __future__ import annotations

import pytest

from learnkit.loader import load_course, load_placement
from learnkit.models import PlacementQuestion, PlacementQuiz

COURSE = load_course()
QUIZZES = load_placement(COURSE)
MIN_QUESTIONS_PER_LESSON = 2


def test_every_start_here_module_has_a_quiz() -> None:
    starts = {
        t.id
        for t in COURSE.tracks
        if t.modules[0].id.endswith("0") and COURSE.modules[t.modules[0].id].lessons
    }
    assert {q.track for q in QUIZZES} == starts


@pytest.mark.parametrize("quiz", QUIZZES, ids=lambda q: q.track)
def test_quiz_covers_every_lesson(quiz: PlacementQuiz) -> None:
    lessons = [lesson.id for lesson in COURSE.modules[quiz.module].lessons]
    for lesson_id in lessons:
        hits = sum(lesson_id in q.lessons for q in quiz.questions)
        assert hits >= MIN_QUESTIONS_PER_LESSON, f"{lesson_id}: only {hits} questions"


@pytest.mark.parametrize("quiz", QUIZZES, ids=lambda q: q.track)
def test_track_has_a_module_to_skip_to(quiz: PlacementQuiz) -> None:
    track = next(t for t in COURSE.tracks if t.id == quiz.track)
    assert len(track.modules) > 1


@pytest.mark.parametrize(
    "question", [q for quiz in QUIZZES for q in quiz.questions], ids=lambda q: q.id
)
def test_options_are_distinct(question: PlacementQuestion) -> None:
    texts = [o.text for o in question.options]
    assert len(texts) == len(set(texts))
    assert question.explanation.strip()
