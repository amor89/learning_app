"""The B21 RAG lab works with the reference solution, and its stubs start empty.

The lab sheet tells learners to fill in src/survey_rag/steps.py until the lab's
tests pass. This test copies the lab, drops in solution/steps.py and runs the
lab's own suite, so the tests, the notes and the gold set stay consistent.
"""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[2] / "labs" / "rag"
STEPS = LAB / "src" / "survey_rag" / "steps.py"
SOLUTION = LAB / "solution" / "steps.py"


def _functions(path: Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_solution_passes_the_lab_suite(tmp_path: Path) -> None:
    """Run the lab's tests in their own process against the reference steps."""
    pytest.importorskip("sklearn")
    lab = tmp_path / "rag"
    shutil.copytree(LAB, lab, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    shutil.copy(SOLUTION, lab / "src" / "survey_rag" / "steps.py")
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    result = subprocess.run(command, cwd=lab, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]


def test_stubs_match_the_solution_and_raise() -> None:
    """Every stub has the solution's signature and only raises NotImplementedError."""
    stubs, solutions = _functions(STEPS), _functions(SOLUTION)
    assert set(stubs) == set(solutions)
    for name, stub in stubs.items():
        assert ast.dump(stub.args) == ast.dump(solutions[name].args), name
        assert ast.dump(stub.returns) == ast.dump(solutions[name].returns), name
        body = [n for n in stub.body if not isinstance(n, ast.Expr)]
        assert len(body) == 1 and isinstance(body[0], ast.Raise), name
