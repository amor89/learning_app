"""Run a Python exercise checker: syntax, static rules, then hidden tests."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import traceback
from dataclasses import asdict, dataclass, field
from typing import Any

from checkers.ast_rules import evaluate_rule

SYNTAX_RULE_ID = "syntax"
RUNTIME_RULE_ID = "runtime_error"
MAX_OUTPUT_CHARS = 4000


@dataclass
class CheckResult:
    """Outcome of one check.

    Attributes:
        passed: True when every rule and test passed.
        rule_id: Id of the first failing rule or test, empty when passed.
        feedback: Message for the first failure, empty when passed.
        failures: Ids of every failing rule and test, for the test suite.
        stdout: Captured output from running the code, truncated.
    """

    passed: bool
    rule_id: str = ""
    feedback: str = ""
    failures: list[str] = field(default_factory=list)
    stdout: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict."""
        return asdict(self)


def _syntax_error(code: str) -> CheckResult | None:
    try:
        ast.parse(code)
    except SyntaxError as err:
        message = f"Syntax error on line {err.lineno}: {err.msg}."
        return CheckResult(False, SYNTAX_RULE_ID, message, [SYNTAX_RULE_ID])
    return None


def _static_failures(code: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tree = ast.parse(code)
    return [rule for rule in rules if not evaluate_rule(tree, code, rule)]


def _short_error(err: BaseException) -> str:
    return f"{type(err).__name__}: {err}"


def _run_tests(code: str, setup: str, tests: list[dict[str, Any]]) -> CheckResult:
    namespace: dict[str, Any] = {"__name__": "__exercise__"}
    buffer = io.StringIO()
    failures: list[str] = []
    first: tuple[str, str] | None = None
    with contextlib.redirect_stdout(buffer):
        try:
            if setup:
                exec(setup, namespace)
            exec(code, namespace)
        except Exception as err:
            last = traceback.extract_tb(err.__traceback__)[-1]
            message = f"Your code raised {_short_error(err)} (line {last.lineno})."
            return CheckResult(False, RUNTIME_RULE_ID, message, [RUNTIME_RULE_ID])
        for test in tests:
            try:
                exec(test["code"], namespace)
            except AssertionError:
                failures.append(test["id"])
                first = first or (test["id"], test["message"])
            except Exception as err:
                failures.append(test["id"])
                first = first or (test["id"], f"{test['message']} ({_short_error(err)})")
    stdout = buffer.getvalue()[:MAX_OUTPUT_CHARS]
    if first:
        return CheckResult(False, first[0], first[1], failures, stdout)
    return CheckResult(True, stdout=stdout)


def check_python(checker: dict[str, Any], code: str) -> CheckResult:
    """Check submitted Python code against an exercise checker.

    Args:
        checker: Checker definition with optional ``ast_rules``, ``setup`` and ``tests``.
        code: The learner's code.

    Returns:
        The first failure in order syntax, static rules, tests, or a pass.
    """
    syntax = _syntax_error(code)
    if syntax:
        return syntax
    static = _static_failures(code, checker.get("ast_rules", []))
    if static:
        ids = [rule["id"] for rule in static]
        return CheckResult(False, static[0]["id"], static[0]["message"], ids)
    tests = checker.get("tests", [])
    if not tests:
        return CheckResult(True)
    return _run_tests(code, checker.get("setup", ""), tests)


def check_python_json(checker_json: str, code: str) -> str:
    """JSON wrapper for the browser worker."""
    return json.dumps(check_python(json.loads(checker_json), code).to_dict())
