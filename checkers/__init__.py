"""Exercise checkers shared by the browser (Pyodide) and the test suite (CPython).

Standard library only, so the package loads in Pyodide without extra wheels.
"""

from checkers.core import CheckResult, check_python, check_python_json

__all__ = ["CheckResult", "check_python", "check_python_json"]
