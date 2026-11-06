"""Pydantic models for lesson content.

The models enforce the lesson format: concept length, exercise count and mix,
three hint tiers, a recap of three to five cards and rising difficulty.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONCEPT_MIN_WORDS = 150
CONCEPT_MAX_WORDS = 300
MIN_EXERCISES = 5
MIN_EXERCISE_TYPES = 3
HINT_TIERS = 3
PRIMER_MAX_WORDS = 120

Language = Literal["python", "pyspark", "sql", "tsql", "kql", "dax", "yaml", "text"]
CommentStyle = Literal["sql", "dax", "kql", "none"]


class Strict(BaseModel):
    """Base model that rejects unknown keys, so typos in YAML fail the build."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def word_count(markdown_text: str) -> int:
    """Count words in Markdown prose, ignoring fenced code blocks."""
    prose = re.sub(r"```.*?```", " ", markdown_text, flags=re.DOTALL)
    return len(re.findall(r"[A-Za-z0-9][\w'\u2019.-]*", prose))


# Checkers -----------------------------------------------------------------


class AstRule(BaseModel):
    """One static rule. Kind-specific keys pass through to the checker."""

    model_config = ConfigDict(extra="allow", frozen=True)

    id: str
    kind: Literal[
        "requires_call",
        "forbids_call",
        "max_calls",
        "requires_import",
        "forbids_import_from",
        "requires_function",
        "forbids_decorator",
        "forbids_compare_to_bool",
        "forbids_mutable_default",
        "forbids_bare_truthiness",
        "requires_pattern",
        "forbids_pattern",
    ]
    message: str


class PythonTest(Strict):
    id: str
    code: str
    message: str


class PythonChecker(Strict):
    kind: Literal["python"]
    ast_rules: list[AstRule] = []
    setup: str = ""
    tests: list[PythonTest] = []

    @model_validator(mode="after")
    def _has_checks(self) -> PythonChecker:
        if not self.ast_rules and not self.tests:
            raise ValueError("a python checker needs ast_rules or tests")
        ids = [r.id for r in self.ast_rules] + [t.id for t in self.tests]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate rule or test ids: {ids}")
        return self


class TextRule(Strict):
    id: str
    type: Literal["required", "forbidden"]
    pattern: str
    message: str

    @model_validator(mode="after")
    def _valid_regex(self) -> TextRule:
        re.compile(self.pattern)
        return self


class TextChecker(Strict):
    kind: Literal["text"]
    comments: CommentStyle = "none"
    rules: list[TextRule]


Checker = Annotated[PythonChecker | TextChecker, Field(discriminator="kind")]


# Exercises ----------------------------------------------------------------


class Option(Strict):
    id: str
    text: str


class ExerciseBase(Strict):
    """Fields every exercise shares.

    ``primer`` explains, with a small example on other data, each function or
    keyword the exercise needs that its lesson has not taught yet.
    """

    id: str
    difficulty: int = Field(ge=1, le=5)
    prompt: str
    primer: str = ""
    hints: list[str]
    explanation: str

    @model_validator(mode="after")
    def _three_hints(self) -> ExerciseBase:
        if len(self.hints) != HINT_TIERS:
            raise ValueError(f"{self.id}: needs exactly {HINT_TIERS} hints")
        if word_count(self.primer) > PRIMER_MAX_WORDS:
            raise ValueError(f"{self.id}: primer prose over {PRIMER_MAX_WORDS} words")
        return self


class Feedback(Strict):
    feedback: str


class McqWrong(Feedback):
    answer: str


class McqExercise(ExerciseBase):
    type: Literal["mcq"]
    options: list[Option]
    answer: str
    reasons: list[Option] = []
    reason_answer: str | None = None
    wrong_answers: list[McqWrong]

    @model_validator(mode="after")
    def _keys_exist(self) -> McqExercise:
        ids = {o.id for o in self.options}
        reason_ids = {r.id for r in self.reasons}
        if self.answer not in ids:
            raise ValueError(f"{self.id}: answer {self.answer} is not an option")
        if bool(self.reasons) != (self.reason_answer is not None):
            raise ValueError(f"{self.id}: reasons and reason_answer go together")
        if self.reason_answer is not None and self.reason_answer not in reason_ids:
            raise ValueError(f"{self.id}: reason_answer is not a reason")
        for wrong in self.wrong_answers:
            option, _, reason = wrong.answer.partition("|")
            if option not in ids or (reason and reason not in reason_ids):
                raise ValueError(f"{self.id}: wrong answer {wrong.answer} is not an option")
        return self


class Gap(Strict):
    accepted: list[str] = Field(min_length=1)
    case_sensitive: bool = True


class FillGapWrong(Feedback):
    answer: dict[str, str]


class FillGapExercise(ExerciseBase):
    type: Literal["fill_gap"]
    language: Language
    template: str
    gaps: dict[str, Gap]
    wrong_answers: list[FillGapWrong]

    @model_validator(mode="after")
    def _gaps_match_template(self) -> FillGapExercise:
        in_template = set(re.findall(r"\[\[(\w+)\]\]", self.template))
        if in_template != set(self.gaps):
            raise ValueError(f"{self.id}: template gaps {in_template} != gaps {set(self.gaps)}")
        return self


class PredictWrong(Feedback):
    answer: str = Field(pattern=r"\S")


class PredictOutputExercise(ExerciseBase):
    type: Literal["predict_output"]
    language: Language
    code: str
    answer: str
    accepted: list[str] = []
    wrong_answers: list[PredictWrong]


class OrderWrong(Feedback):
    answer: list[str]


class OrderExercise(ExerciseBase):
    type: Literal["order"]
    items: list[Option]
    answer: list[str]
    wrong_answers: list[OrderWrong]

    @model_validator(mode="after")
    def _answer_is_permutation(self) -> OrderExercise:
        ids = sorted(o.id for o in self.items)
        if sorted(self.answer) != ids:
            raise ValueError(f"{self.id}: answer must list every item once")
        for wrong in self.wrong_answers:
            if sorted(wrong.answer) != ids:
                raise ValueError(f"{self.id}: wrong answer must list every item once")
        return self


class SpotBugWrong(Feedback):
    lines: list[int]


class SpotBugExercise(ExerciseBase):
    type: Literal["spot_bug"]
    language: Language
    code: str
    bug_lines: list[int] = Field(min_length=1)
    packages: list[str] = []
    fix_checker: Checker | None = None
    fix_solution: str = ""
    fix_seeded_bugs: list[str] = []
    spark_tests: str = ""
    wrong_answers: list[SpotBugWrong]

    @model_validator(mode="after")
    def _lines_in_range(self) -> SpotBugExercise:
        n_lines = len(self.code.rstrip("\n").split("\n"))
        for line in [*self.bug_lines, *(n for w in self.wrong_answers for n in w.lines)]:
            if not 1 <= line <= n_lines:
                raise ValueError(f"{self.id}: line {line} outside 1..{n_lines}")
        if self.fix_checker and not self.fix_solution:
            raise ValueError(f"{self.id}: a fix_checker needs a fix_solution")
        return self


class CodeWrong(Strict):
    answer: str
    triggers: str


class CodeExercise(ExerciseBase):
    type: Literal["write_function", "refactor"]
    language: Language
    starter: str = ""
    packages: list[str] = []
    checker: Checker
    solution: str
    spark_tests: str = ""
    seeded_bugs: list[str] = Field(min_length=1)
    wrong_answers: list[CodeWrong] = []

    @model_validator(mode="after")
    def _triggers_exist(self) -> CodeExercise:
        if isinstance(self.checker, PythonChecker):
            ids = {r.id for r in self.checker.ast_rules} | {t.id for t in self.checker.tests}
            ids |= {"syntax", "runtime_error"}
        else:
            ids = {r.id for r in self.checker.rules}
        for wrong in self.wrong_answers:
            if wrong.triggers not in ids:
                raise ValueError(f"{self.id}: triggers {wrong.triggers} is not a rule id")
        return self


class Slot(Strict):
    id: str
    label: str
    options: list[Option]
    answer: str


class DesignWrong(Feedback):
    answer: dict[str, str]


class DesignExercise(ExerciseBase):
    type: Literal["design"]
    slots: list[Slot]
    model_answer: str
    wrong_answers: list[DesignWrong]

    @model_validator(mode="after")
    def _answers_are_options(self) -> DesignExercise:
        for slot in self.slots:
            if slot.answer not in {o.id for o in slot.options}:
                raise ValueError(f"{self.id}: slot {slot.id} answer is not an option")
        return self


Exercise = Annotated[
    McqExercise
    | FillGapExercise
    | PredictOutputExercise
    | OrderExercise
    | SpotBugExercise
    | CodeExercise
    | DesignExercise,
    Field(discriminator="type"),
]


# Lesson -------------------------------------------------------------------


class Annotation(Strict):
    """A note on the one line of code that contains ``find``."""

    find: str
    note: str


class CodeSample(Strict):
    code: str
    annotations: list[Annotation] = Field(min_length=1)

    def annotated_lines(self) -> list[tuple[int, str]]:
        """Resolve each annotation to a 1-based line number.

        Raises:
            ValueError: If a ``find`` fragment matches no line or several lines.
        """
        lines = self.code.rstrip("\n").split("\n")
        resolved: list[tuple[int, str]] = []
        for ann in self.annotations:
            hits = [i + 1 for i, text in enumerate(lines) if ann.find in text]
            if len(hits) != 1:
                raise ValueError(f"annotation {ann.find!r} matches lines {hits}, needs one")
            resolved.append((hits[0], ann.note))
        return sorted(resolved)

    @model_validator(mode="after")
    def _annotations_resolve(self) -> CodeSample:
        self.annotated_lines()
        return self


class WorkedExample(Strict):
    language: Language
    weak: CodeSample
    strong: CodeSample
    takeaway: str


class RecapCard(Strict):
    front: str
    back: str


class Claim(Strict):
    """An API or platform fact the lesson relies on, with its verification status."""

    claim: str
    status: Literal["verified", "search-only", "unverified"]
    source: str


class NotebookCell(Strict):
    kind: Literal["markdown", "code"]
    source: str


class Practical(Strict):
    platform: Literal["databricks", "fabric", "laptop"]
    title: str
    intro: str
    cells: list[NotebookCell] = []
    steps: list[str] = []


class Lesson(Strict):
    id: str
    title: str
    concept: str
    why_it_matters: str
    worked_example: WorkedExample
    exercises: list[Exercise]
    recap: list[RecapCard] = Field(min_length=3, max_length=5)
    claims: list[Claim] = []
    practical: Practical | None = None

    @model_validator(mode="after")
    def _lesson_rules(self) -> Lesson:
        words = word_count(self.concept)
        if not CONCEPT_MIN_WORDS <= words <= CONCEPT_MAX_WORDS:
            raise ValueError(f"{self.id}: concept has {words} words, needs 150 to 300")
        if len(self.exercises) < MIN_EXERCISES:
            raise ValueError(f"{self.id}: needs at least {MIN_EXERCISES} exercises")
        if len({e.type for e in self.exercises}) < MIN_EXERCISE_TYPES:
            raise ValueError(f"{self.id}: needs at least {MIN_EXERCISE_TYPES} exercise types")
        levels = [e.difficulty for e in self.exercises]
        if levels != sorted(levels):
            raise ValueError(f"{self.id}: difficulty must rise, got {levels}")
        ids = [e.id for e in self.exercises]
        if len(ids) != len(set(ids)) or not all(i.startswith(f"{self.id}-") for i in ids):
            raise ValueError(f"{self.id}: exercise ids must be unique and prefixed {self.id}-")
        return self


# Tracks -------------------------------------------------------------------


class ModuleMeta(Strict):
    id: str
    title: str
    tags: list[str]
    summary: str


class Track(Strict):
    id: str
    title: str
    summary: str
    checklist: list[str]
    modules: list[ModuleMeta]


class Band(Strict):
    id: str
    label: str


class Roadmap(Strict):
    bands: list[Band]


class Stage(Strict):
    """One step of a pathway: an ordered group of modules."""

    id: str
    title: str
    summary: str
    modules: list[str] = Field(min_length=1)


class Pathway(Strict):
    """An ordered route through modules towards one goal."""

    id: str
    title: str
    summary: str
    stages: list[Stage] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> Pathway:
        stage_ids = [s.id for s in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError(f"{self.id}: stage ids must be unique")
        modules = [m for s in self.stages for m in s.modules]
        repeats = sorted({m for m in modules if modules.count(m) > 1})
        if repeats:
            raise ValueError(f"{self.id}: modules listed twice: {repeats}")
        return self


class Pathways(Strict):
    """Every pathway, in the order the app lists them."""

    pathways: list[Pathway] = Field(min_length=1)


# Interview practice -------------------------------------------------------

MIN_POINTS = 2
MAX_POINTS = 5
MIN_OPTIONS = 3
TASK_PRIMER_MAX_WORDS = 150


class InterviewTopic(Strict):
    """A group of theory questions, such as statistics or transformers."""

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str


class TheoryQuestion(Strict):
    """One timed theory question.

    A question with ``options`` is multiple choice and graded by the app. A
    question with ``points`` is open: you answer aloud, then tick the key points
    your answer covered. ``lessons`` name the lessons that teach the answer.
    """

    id: str
    lessons: list[str] = Field(min_length=1)
    seconds: int = Field(ge=20, le=300)
    question: str
    options: list[Option] = []
    answer: str | None = None
    points: list[str] = []
    model_answer: str

    @model_validator(mode="after")
    def _one_format(self) -> TheoryQuestion:
        if self.options:
            if len(self.options) < MIN_OPTIONS:
                raise ValueError(f"{self.id}: needs at least {MIN_OPTIONS} options")
            if self.answer not in {o.id for o in self.options}:
                raise ValueError(f"{self.id}: answer {self.answer} is not an option")
            if self.points:
                raise ValueError(f"{self.id}: a multiple-choice question has no points")
        else:
            if self.answer is not None:
                raise ValueError(f"{self.id}: an open question has no answer key")
            if not MIN_POINTS <= len(self.points) <= MAX_POINTS:
                raise ValueError(f"{self.id}: needs {MIN_POINTS} to {MAX_POINTS} points")
        return self

    @property
    def kind(self) -> Literal["mcq", "open"]:
        """Multiple choice or open."""
        return "mcq" if self.options else "open"


class TheoryFile(Strict):
    """The questions of one topic, in content/interview/theory/<topic>.yaml."""

    topic: str
    questions: list[TheoryQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids(self) -> TheoryFile:
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)) or not all(i.startswith(f"{self.topic}-") for i in ids):
            prefix = f"{self.topic}-"
            raise ValueError(f"{self.topic}: question ids must be unique and prefixed {prefix}")
        return self


class FollowUp(Strict):
    """A question an interviewer asks once your code works, with a model answer."""

    question: str
    answer: str


class InterviewTask(Strict):
    """A timed "implement it from scratch" task, checked by the Python checker.

    ``primer`` reminds you of the algorithm, not the code. The app hides it
    until you ask, and records that you did.
    """

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    lessons: list[str] = Field(min_length=1)
    minutes: int = Field(ge=5, le=60)
    prompt: str
    primer: str = ""
    starter: str
    packages: list[str] = []
    checker: PythonChecker
    solution: str
    seeded_bugs: list[str] = Field(min_length=1)
    wrong_answers: list[CodeWrong] = []
    hints: list[str]
    explanation: str
    follow_ups: list[FollowUp] = Field(min_length=2)

    @model_validator(mode="after")
    def _task_rules(self) -> InterviewTask:
        if len(self.hints) != HINT_TIERS:
            raise ValueError(f"{self.id}: needs exactly {HINT_TIERS} hints")
        if word_count(self.primer) > TASK_PRIMER_MAX_WORDS:
            raise ValueError(f"{self.id}: primer prose over {TASK_PRIMER_MAX_WORDS} words")
        ids = {r.id for r in self.checker.ast_rules} | {t.id for t in self.checker.tests}
        ids |= {"syntax", "runtime_error"}
        for wrong in self.wrong_answers:
            if wrong.triggers not in ids:
                raise ValueError(f"{self.id}: triggers {wrong.triggers} is not a rule id")
        return self


class InterviewIndex(Strict):
    """content/interview/index.yaml: topic order and task order."""

    topics: list[InterviewTopic] = Field(min_length=1)
    tasks: list[str] = Field(min_length=1)


def exercise_summary(exercise: Any) -> dict[str, Any]:
    """Short dict used in indexes and tests."""
    return {"id": exercise.id, "type": exercise.type, "difficulty": exercise.difficulty}
