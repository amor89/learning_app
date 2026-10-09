"""The brief shown before every code editor."""

import re

import pytest

from learnkit.brief import NAME_LINE, code_brief, fix_brief, signature, solution_shape, text_outline
from learnkit.loader import load_course
from learnkit.models import CodeExercise, PythonChecker, SpotBugExercise

# A bare keyword line (SELECT), a table name (KQL) or a measure header (DAX).
OPEN_LINE = re.compile(rf"^[A-Z]+$|{NAME_LINE.pattern}")
COURSE = load_course()
CODE = [
    ex for lesson in COURSE.lessons() for ex in lesson.exercises if isinstance(ex, CodeExercise)
]
FIXES = [
    ex
    for lesson in COURSE.lessons()
    for ex in lesson.exercises
    if isinstance(ex, SpotBugExercise) and ex.fix_checker
]


@pytest.mark.parametrize("ex", CODE, ids=lambda ex: ex.id)
def test_every_code_exercise_has_a_brief(ex: CodeExercise) -> None:
    """Steps, one line per behaviour test, and a non-empty shape of the answer."""
    brief = code_brief(ex)
    assert len(brief.steps) == 3
    if isinstance(ex.checker, PythonChecker):
        assert brief.must == [t.message for t in ex.checker.tests]
    assert brief.shape, f"{ex.id}: no shape derived from the solution"
    assert brief.shape_note


@pytest.mark.parametrize("ex", CODE, ids=lambda ex: ex.id)
def test_shape_never_prints_the_solution_body(ex: CodeExercise) -> None:
    """The shape holds stubs or clause keywords, never a line of the answer's body."""
    for d in code_brief(ex).shape:
        for line in d.code.split("\n"):
            if isinstance(ex.checker, PythonChecker):
                assert re.match(
                    r"(async def |def |class |[A-Z_0-9]+ = \.\.\.$|    \S|\) )", line
                ), line
            else:
                assert not line.strip() or line.endswith("...") or OPEN_LINE.match(line), line


@pytest.mark.parametrize("ex", FIXES, ids=lambda ex: ex.id)
def test_fix_brief_has_no_shape(ex: SpotBugExercise) -> None:
    """The fix step never shows the shape, which would point at the bug."""
    brief = fix_brief(ex)
    assert brief is not None
    assert brief.shape == []


def test_sealed_modules_hide_the_shape() -> None:
    """With show_shape off, as in D7 and X3, nothing from the solution appears."""
    assert all(code_brief(ex, show_shape=False).shape == [] for ex in CODE)


def test_long_signature_wraps_one_parameter_per_line() -> None:
    """A signature wider than 60 characters fits a phone screen."""
    shape = solution_shape(
        "def run(spark: str, run_id: str, rows: int, error: str | None = None) -> str:\n"
        '    """One row."""\n'
        "    return run_id\n"
    )
    assert shape[0].code == (
        "def run(\n"
        "    spark: str,\n"
        "    run_id: str,\n"
        "    rows: int,\n"
        "    error: str | None = None,\n"
        ") -> str: ..."
    )
    assert shape[0].summary == "One row."


def test_short_signature_stays_on_one_line() -> None:
    """Defaults without annotations take no spaces around the equals sign."""
    import ast

    node = ast.parse("def f(a, b=1, *, c: int = 2): pass").body[0]
    assert isinstance(node, ast.FunctionDef)
    assert signature(node) == "def f(a, b=1, *, c: int = 2)"


def test_constants_and_classes_appear_in_the_shape() -> None:
    """Upper-case module constants and classes are part of the answer's layout."""
    shape = solution_shape('LIMIT = 3\nclass Rule(Base):\n    """A rule."""\n')
    assert [d.code for d in shape] == ["LIMIT = ...", "class Rule(Base): ..."]


@pytest.mark.parametrize(
    ("source", "outline"),
    [
        (
            "SELECT customer_id, COUNT(*) AS n\nFROM dbo.t\nGROUP BY customer_id\n"
            "HAVING COUNT(*) > 1;\n",
            "SELECT ...\nFROM ...\nGROUP BY ...\nHAVING ...",
        ),
        ("t\n| where x > 1\n| summarize n = count()\n", "t\n| where ...\n| summarize ..."),
        ("M =\nVAR a = [X]\nRETURN DIVIDE ( a, 2 )\n", "M =\nVAR ...\nRETURN ..."),
        ("SELECT\n    a,\n    b\nFROM t\n", "SELECT\n    ...\nFROM ..."),
    ],
)
def test_text_outline_keeps_clauses_only(source: str, outline: str) -> None:
    """SQL, KQL and DAX outlines keep clause keywords and drop the details."""
    assert text_outline(source) == outline
