"""Unit tests for the static rules and the check runner."""

from __future__ import annotations

from typing import Any

import pytest

from checkers import check_python


def rule(kind: str, **extra: Any) -> dict[str, Any]:
    return {"id": kind, "kind": kind, "message": f"{kind} failed", **extra}


@pytest.mark.parametrize(
    ("the_rule", "good", "bad"),
    [
        (rule("requires_call", name="F.broadcast"), "F.broadcast(df)", "broadcast(df)"),
        (rule("requires_call", name="desc"), "F.col('a').desc()", "F.col('a')"),
        (rule("forbids_call", name="collect"), "df.count()", "df.collect()"),
        (rule("max_calls", name="count", max=1), "df.count()", "df.count()\ndf.count()"),
        (
            rule("requires_import", module="pyspark.sql", name="functions", alias="F"),
            "from pyspark.sql import functions as F",
            "from pyspark.sql import functions",
        ),
        (
            rule("forbids_import_from", module="pyspark.sql.functions", names=["sum"]),
            "from pyspark.sql.functions import col",
            "from pyspark.sql.functions import col, sum",
        ),
        (
            rule("forbids_import_from", module="pyspark.sql.functions", names=["sum"]),
            "import os",
            "from pyspark.sql.functions import *",
        ),
        (
            rule("requires_function", name="f", typed=True, docstring=True),
            'def f(a: int) -> int:\n    """Doc."""\n    return a',
            "def f(a):\n    return a",
        ),
        (rule("forbids_decorator", name="udf"), "def f(): pass", "@F.udf('int')\ndef f(): pass"),
        (rule("forbids_compare_to_bool"), "df.filter(F.col('x'))", "df.filter(F.col('x') == True)"),
        (rule("forbids_mutable_default"), "def f(a=None): pass", "def f(a=[]): pass"),
        (rule("forbids_mutable_default"), "def f(*, a=None): pass", "def f(*, a={}): pass"),
        (
            rule("forbids_bare_truthiness", names=["x"]),
            "if x is not None:\n    pass",
            "if x and y:\n    pass",
        ),
        (rule("requires_pattern", pattern=r"t\.id\s*="), "'t.id = s.id'", "'s.id'"),
        (rule("forbids_pattern", pattern=r"\bUPDATE\b"), "'SELECT'", "'UPDATE t'"),
    ],
)
def test_rule(the_rule: dict[str, Any], good: str, bad: str) -> None:
    checker = {"ast_rules": [the_rule]}
    assert check_python(checker, good).passed
    result = check_python(checker, bad)
    assert not result.passed
    assert result.rule_id == the_rule["id"]


def test_syntax_error_is_reported() -> None:
    result = check_python({"ast_rules": []}, "def f(:\n")
    assert result.rule_id == "syntax"
    assert "line 1" in result.feedback


def test_runtime_error_is_reported() -> None:
    checker = {"tests": [{"id": "t", "code": "assert True", "message": "m"}]}
    result = check_python(checker, "x = 1 / 0")
    assert result.rule_id == "runtime_error"
    assert "ZeroDivisionError" in result.feedback


def test_first_failing_test_wins_and_all_are_listed() -> None:
    checker = {
        "tests": [
            {"id": "a", "code": "assert x == 2", "message": "a failed"},
            {"id": "b", "code": "assert x == 3", "message": "b failed"},
        ]
    }
    result = check_python(checker, "x = 1")
    assert result.rule_id == "a"
    assert result.failures == ["a", "b"]


def test_error_in_test_includes_exception() -> None:
    checker = {"tests": [{"id": "a", "code": "assert f() == 1", "message": "call f"}]}
    result = check_python(checker, "x = 1")
    assert result.rule_id == "a"
    assert "NameError" in result.feedback


def test_stdout_is_captured() -> None:
    checker = {"tests": [{"id": "a", "code": "assert True", "message": "m"}]}
    assert check_python(checker, "print('hello')").stdout == "hello\n"


def test_dataclass_in_submitted_code() -> None:
    """Regression: dataclasses look up the defining module in sys.modules."""
    checker = {"tests": [{"id": "a", "code": "assert Cfg(1).x == 1", "message": "m"}]}
    code = "from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass Cfg:\n    x: int\n"
    assert check_python(checker, code).passed
