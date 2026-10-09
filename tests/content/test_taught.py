"""Every exercise uses only what a lesson or its primer has explained."""

from learnkit.loader import load_course
from learnkit.taught import python_names, sql_names, untaught


def test_every_exercise_uses_only_taught_names() -> None:
    """An exercise needing an unexplained function or keyword fails the build.

    Fix a failure with a `primer` on the exercise: a short explanation and an
    example on other data.
    """
    gaps = untaught(load_course())
    report = "\n".join(f"{ex_id}: {', '.join(names)}" for ex_id, names in gaps.items())
    assert not gaps, f"Untaught names. Add a primer to each exercise:\n{report}"


def test_python_names_skip_core_python_and_helpers() -> None:
    """str and list methods, built-ins and the exercise's own helpers are known."""
    code = "import tomllib\nrows = check(x)\nrows.append(1)\ndata = tomllib.loads(t).get('a')\n"
    assert python_names(code) == {"tomllib", "loads"}


def test_sql_names_skip_core_sql_and_defined_functions() -> None:
    """Core SQL keywords and functions the snippet creates are known."""
    code = "CREATE FUNCTION f(x INT) RETURN x;\nSELECT NULLIF(SUM(a), 0) FROM t WHERE f(a) > 1;"
    assert sql_names(code) == {"FUNCTION", "RETURN", "NULLIF"}
