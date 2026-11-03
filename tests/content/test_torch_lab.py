"""The B23 PyTorch lab works with the reference solution, and its stubs start empty.

The dev environment has no PyTorch, so in CI the NumPy tests run and the
PyTorch tests skip. Run this file in an environment with PyTorch 2.15 to
check the whole lab.
"""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[2] / "labs" / "torch"
MODULES = ["prep.py", "nn_steps.py"]


def _definitions(path: Path) -> dict[str, ast.FunctionDef]:
    """Top-level functions and class methods, keyed by qualified name."""
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    found[f"{node.name}.{item.name}"] = item
    return found


def test_solution_passes_the_lab_suite(tmp_path: Path) -> None:
    """Run the lab's tests in their own process against the reference steps."""
    pytest.importorskip("sklearn")
    lab = tmp_path / "torch"
    shutil.copytree(LAB, lab, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    for name in MODULES:
        shutil.copy(LAB / "solution" / name, lab / "src" / "survey_torch" / name)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    result = subprocess.run(command, cwd=lab, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert " passed" in result.stdout, result.stdout[-1000:]


@pytest.mark.parametrize("name", MODULES)
def test_stubs_match_the_solution_and_raise(name: str) -> None:
    """Every stub has the solution's signature and only raises NotImplementedError."""
    stubs = _definitions(LAB / "src" / "survey_torch" / name)
    solutions = _definitions(LAB / "solution" / name)
    assert set(stubs) == set(solutions)
    for key, stub in stubs.items():
        assert ast.dump(stub.args) == ast.dump(solutions[key].args), key
        assert ast.dump(stub.returns) == ast.dump(solutions[key].returns), key
        body = [n for n in stub.body if not isinstance(n, ast.Expr)]
        assert len(body) == 1 and isinstance(body[0], ast.Raise), key
