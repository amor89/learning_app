"""The briefing a learner reads before a code exercise's editor.

Everything comes from fields the exercise already has, so the app and the
handbook show the same text and nobody writes it twice:

- ``must``: the message of every behaviour test, in order.
- ``checks``: the test code itself, for learners who want a concrete example.
- ``shape``: the top-level definitions of the reference solution (signature
  and first docstring line), so the learner sees how the answer is laid out.
  For SQL, DAX and KQL it is an outline of the solution's clauses.
- ``include`` and ``avoid``: the static rule messages, as an opt-in checklist.
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from learnkit.models import Checker, CodeExercise, PythonChecker, SpotBugExercise

FORBIDDING_KINDS = {
    "forbids_call",
    "forbids_import_from",
    "forbids_decorator",
    "forbids_compare_to_bool",
    "forbids_mutable_default",
    "forbids_bare_truthiness",
    "forbids_pattern",
    "max_calls",
}

SIGNATURE_WIDTH = 60
OUTLINE_KEYWORDS = 3
PYTHON_SHAPE_NOTE = "The reference solution defines these names. Write the bodies yourself."
TEXT_SHAPE_NOTE = "The reference answer follows this outline. Replace each ... with your own code."
LEADING_KEYWORDS = re.compile(r"^(\s*)((?:[A-Z]+(?!\s*\()(?=\s|$)\s*)+)")
KQL_OPERATOR = re.compile(r"^(\s*\|\s*[\w-]+)")
NAME_LINE = re.compile(r"^\w+$|^\S[^=]*=$")

STEPS = {
    "write_function": [
        "Read what your code must do. Each line is one check.",
        "Edit the starter code in the editor. Keep the names it uses.",
        "Tap Run checks. A failed check tells you what to change next.",
    ],
    "refactor": [
        "Read what your code must do. The behaviour stays the same.",
        "Change the structure of the starter code, one step at a time.",
        "Tap Run checks after each step. A failed check names the problem.",
    ],
    "fix": [
        "Change only the line you marked, and the lines it affects.",
        "Keep the rest of the code as it is.",
        "Tap Run checks. A failed check tells you what is still wrong.",
    ],
}


@dataclass(frozen=True)
class Definition:
    """One top-level name in the reference solution.

    Attributes:
        code: A stub, for example ``def f(x: int) -> str: ...``.
        summary: The first line of its docstring, or an empty string.
    """

    code: str
    summary: str


@dataclass(frozen=True)
class Check:
    """One behaviour test shown as an example."""

    message: str
    code: str


@dataclass(frozen=True)
class Brief:
    """What the learner sees between the prompt and the editor."""

    steps: list[str]
    must: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    shape: list[Definition] = field(default_factory=list)
    shape_note: str = ""
    include: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """Return the brief as plain JSON data."""
        return asdict(self)


def parameter(arg: ast.arg, default: ast.expr | None) -> str:
    """Format one parameter the way ``ruff format`` writes it."""
    text = arg.arg
    if arg.annotation is not None:
        text += f": {ast.unparse(arg.annotation)}"
    if default is not None:
        text += (" = " if arg.annotation is not None else "=") + ast.unparse(default)
    return text


def parameters(args: ast.arguments) -> list[str]:
    """Format every parameter of a function, markers included."""
    positional = [*args.posonlyargs, *args.args]
    padding: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults))
    parts = []
    for i, (arg, default) in enumerate(zip(positional, [*padding, *args.defaults], strict=True)):
        parts.append(parameter(arg, default))
        if args.posonlyargs and i == len(args.posonlyargs) - 1:
            parts.append("/")
    if args.vararg:
        parts.append("*" + parameter(args.vararg, None))
    elif args.kwonlyargs:
        parts.append("*")
    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        parts.append(parameter(arg, kw_default))
    if args.kwarg:
        parts.append("**" + parameter(args.kwarg, None))
    return parts


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return a function's ``def`` line without decorators or body.

    A signature wider than ``SIGNATURE_WIDTH`` puts one parameter per line,
    so it fits a phone screen.
    """
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    parts = parameters(node.args)
    one_line = f"{prefix} {node.name}({', '.join(parts)}){returns}"
    if len(one_line) <= SIGNATURE_WIDTH or not parts:
        return one_line
    body = "".join(f"    {part},\n" for part in parts)
    return f"{prefix} {node.name}(\n{body}){returns}"


def first_line(node: ast.AST) -> str:
    """Return the first docstring line of a definition, if it has one."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        doc = ast.get_docstring(node)
        if doc:
            return doc.strip().splitlines()[0]
    return ""


def solution_shape(source: str) -> list[Definition]:
    """List the functions, classes and constants a Python solution defines.

    Args:
        source: The reference solution.

    Returns:
        One entry per top-level definition, in source order. Empty when the
        source does not parse.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    shape: list[Definition] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            shape.append(Definition(f"{signature(node)}: ...", first_line(node)))
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            head = f"class {node.name}({bases})" if bases else f"class {node.name}"
            shape.append(Definition(f"{head}: ...", first_line(node)))
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    shape.append(Definition(f"{target.id} = ...", "Module constant."))
    return shape


def outline_line(line: str) -> str:
    """Reduce one line of SQL, DAX or KQL to its leading keywords."""
    if not line.strip() or NAME_LINE.match(line.rstrip()):
        return line.rstrip()
    operator = KQL_OPERATOR.match(line)
    if operator:
        return f"{operator.group(1)} ..."
    keywords = LEADING_KEYWORDS.match(line)
    if keywords:
        words = keywords.group(2).split()[:OUTLINE_KEYWORDS]
        return f"{keywords.group(1)}{' '.join(words)} ..."
    indent = line[: len(line) - len(line.lstrip())]
    return f"{indent}..."


def text_outline(source: str) -> str:
    """Outline a SQL, DAX or KQL answer: clause order without the details.

    Args:
        source: The reference solution.

    Returns:
        One line per clause. Runs of detail lines collapse into one ``...``.
    """
    lines: list[str] = []
    for line in source.rstrip("\n").split("\n"):
        outlined = outline_line(line)
        if lines and outlined.strip() == "..." and lines[-1].strip() == "...":
            continue
        lines.append(outlined)
    return "\n".join(lines)


def checker_parts(checker: Checker) -> tuple[list[Check], list[str], list[str]]:
    """Split a checker into behaviour tests, required rules and forbidden rules."""
    if isinstance(checker, PythonChecker):
        checks = [Check(t.message, t.code.rstrip("\n")) for t in checker.tests]
        include = [r.message for r in checker.ast_rules if r.kind not in FORBIDDING_KINDS]
        avoid = [r.message for r in checker.ast_rules if r.kind in FORBIDDING_KINDS]
        return checks, include, avoid
    include = [r.message for r in checker.rules if r.type == "required"]
    avoid = [r.message for r in checker.rules if r.type == "forbidden"]
    return [], include, avoid


def code_brief(ex: CodeExercise, show_shape: bool = True) -> Brief:
    """Build the brief for a write_function or refactor exercise.

    Args:
        ex: The exercise.
        show_shape: False in modules whose answer key is sealed.

    Returns:
        The brief.
    """
    checks, include, avoid = checker_parts(ex.checker)
    shape: list[Definition] = []
    note = ""
    if show_shape and isinstance(ex.checker, PythonChecker):
        shape, note = solution_shape(ex.solution), PYTHON_SHAPE_NOTE
    elif show_shape:
        shape, note = [Definition(text_outline(ex.solution), "")], TEXT_SHAPE_NOTE
    return Brief(
        steps=STEPS[ex.type],
        must=[c.message for c in checks],
        checks=checks,
        shape=shape,
        shape_note=note if shape else "",
        include=include,
        avoid=avoid,
    )


def fix_brief(ex: SpotBugExercise) -> Brief | None:
    """Build the brief for the fix step of a spot-the-bug exercise.

    Returns:
        None when the exercise has no fix step. Never includes the shape,
        which would point at the bug.
    """
    if ex.fix_checker is None:
        return None
    checks, include, avoid = checker_parts(ex.fix_checker)
    return Brief(
        steps=STEPS["fix"],
        must=[c.message for c in checks],
        checks=checks,
        include=include,
        avoid=avoid,
    )
