"""Find what an exercise asks you to use before any lesson has explained it.

An exercise may only use a function, method, import or keyword that one of
these has explained first:

- the lesson's concept, why-it-matters text, worked example or recap;
- the primer of this exercise or an earlier exercise in the same lesson;
- an earlier lesson in the same track. Track D builds on A, B and C, and the
  capstones in X build on A to D, so they count every lesson of those too.

In a spot-the-bug exercise the buggy lines are the point, often an invented
function, so only the other lines and the fixed version count.

Core Python (built-ins and the methods of ``str``, ``list``, ``dict``, ``set``
and ``tuple``) and core SQL keywords count as known.
"""

from __future__ import annotations

import ast
import builtins
import re
from collections.abc import Iterable

from learnkit.loader import Course
from learnkit.models import (
    CodeExercise,
    Exercise,
    FillGapExercise,
    Lesson,
    PredictOutputExercise,
    PythonChecker,
    SpotBugExercise,
)

PYTHON_LANGUAGES = {"python", "pyspark"}
SQL_LANGUAGES = {"sql", "tsql", "kql", "dax"}
BUILDS_ON = {"D": ["A", "B", "C"], "X": ["A", "B", "C", "D"]}
CORE_PYTHON = (
    set(dir(builtins))
    | {name for kind in (str, list, dict, set, tuple, int, float) for name in dir(kind)}
    | {"self", "cls"}
)
CORE_SQL = {
    "SELECT", "FROM", "WHERE", "GROUP", "BY", "ORDER", "HAVING", "AS", "AND", "OR", "NOT",
    "IN", "IS", "NULL", "ON", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "DISTINCT",
    "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE", "TABLE", "VIEW", "DROP",
    "IF", "EXISTS", "REPLACE", "CASE", "WHEN", "THEN", "ELSE", "END", "ASC", "DESC", "LIMIT",
    "TOP", "UNION", "ALL", "BETWEEN", "LIKE", "WITH", "INT", "INTEGER", "BIGINT", "STRING",
    "VARCHAR", "DOUBLE", "FLOAT", "DECIMAL", "DATE", "TIMESTAMP", "BOOLEAN", "TRUE", "FALSE",
    "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "CAST",
    "count", "sum", "avg", "min", "max", "round", "cast",
}  # fmt: skip
SQL_TOKEN = re.compile(r"\b([A-Z][A-Z_]{2,})\b|\b([a-z][a-z_0-9]*)\s*\(")


def python_names(code: str) -> set[str]:
    """Library names a Python snippet uses.

    That is: methods called, names imported, and attributes reached through an
    imported module, such as ``ast.Call`` or ``inspect.Parameter.VAR_KEYWORD``.

    Plain calls to names the snippet never imports (``check(df)``) are the
    exercise's own helpers, so they do not count.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            chain: list[str] = []
            part: ast.expr = node
            while isinstance(part, ast.Attribute):
                chain.append(part.attr)
                part = part.value
            if isinstance(part, ast.Name) and part.id in imported:
                names |= set(chain)
    plain_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    helpers = plain_calls - imported
    return {n for n in names - helpers - CORE_PYTHON if not n.startswith("_")}


def sql_names(code: str) -> set[str]:
    """Keywords and functions a SQL, KQL or DAX snippet uses, minus core SQL."""
    code = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", " ", code)
    defined = set(re.findall(r"(?:FUNCTION|TABLE|INTO|VIEW)\s+(?:[\w.]+\.)?(\w+)", code))
    found = {upper or lower for upper, lower in SQL_TOKEN.findall(code)}
    return found - CORE_SQL - defined


def snippets(ex: Exercise) -> tuple[list[str], str]:
    """The code a learner reads or writes for one exercise, and its language."""
    if isinstance(ex, CodeExercise):
        return [ex.solution], ex.language
    if isinstance(ex, SpotBugExercise):
        lines = ex.code.rstrip("\n").split("\n")
        kept = "\n".join("" if n in ex.bug_lines else line for n, line in enumerate(lines, 1))
        return [kept, ex.fix_solution], ex.language
    if isinstance(ex, PredictOutputExercise):
        return [ex.code], ex.language
    if isinstance(ex, FillGapExercise):
        filled = ex.template
        for gap, spec in ex.gaps.items():
            filled = filled.replace(f"[[{gap}]]", spec.accepted[0])
        return [filled], ex.language
    return [], ""


def used_names(ex: Exercise) -> set[str]:
    """Names an exercise needs, excluding those its own setup defines."""
    code, language = snippets(ex)
    if language in PYTHON_LANGUAGES:
        names = set().union(*(python_names(c) for c in code if c))
        checker = getattr(ex, "checker", None) or getattr(ex, "fix_checker", None)
        if isinstance(checker, PythonChecker) and checker.setup:
            names -= defined_names(checker.setup)
        return names
    if language in SQL_LANGUAGES:
        names = set().union(*(sql_names(c) for c in code if c))
        return {n for n in names if not re.search(rf"`[^`]*\b{re.escape(n)}\b", ex.prompt)}
    return set()


def defined_names(code: str) -> set[str]:
    """Functions, classes and variables a snippet defines."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            out.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            out.add(node.id)
    return out


def lesson_text(lesson: Lesson) -> str:
    """Everything a lesson explains before its exercises."""
    example = lesson.worked_example
    notes = [a.note for side in (example.weak, example.strong) for a in side.annotations]
    parts = [
        lesson.concept,
        lesson.why_it_matters,
        example.weak.code,
        example.strong.code,
        example.takeaway,
        *notes,
        *(f"{c.front} {c.back}" for c in lesson.recap),
    ]
    return "\n".join(parts)


def explained(name: str, text: str) -> bool:
    """True when the name appears as a whole word in the taught text."""
    return re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)|\.{re.escape(name)}\b", text) is not None


def untaught(course: Course) -> dict[str, list[str]]:
    """Map each exercise id to the names it uses before anything explained them.

    Returns:
        Only exercises with at least one untaught name, in syllabus order.
    """
    by_track: dict[str, list[Lesson]] = {}
    for module in course.modules.values():
        by_track.setdefault(module.track_id, []).extend(module.lessons)
    gaps: dict[str, list[str]] = {}
    for track, lessons in by_track.items():
        earlier = "\n".join(
            lesson_text(lesson) + primers(lesson.exercises)
            for base in BUILDS_ON.get(track, [])
            for lesson in by_track.get(base, [])
        )
        for lesson in lessons:
            known = earlier + "\n" + lesson_text(lesson)
            for ex in lesson.exercises:
                known += "\n" + ex.primer
                missing = sorted(n for n in used_names(ex) if not explained(n, known))
                if missing:
                    gaps[ex.id] = missing
            earlier += "\n" + lesson_text(lesson) + primers(lesson.exercises)
    return gaps


def primers(exercises: Iterable[Exercise]) -> str:
    """All primer text of a lesson's exercises."""
    return "\n".join(ex.primer for ex in exercises)
