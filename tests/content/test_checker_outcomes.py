"""The checker reports pytest outcome exceptions as failed checks, not crashes."""

from checkers.core import check_python

CHECKER = {
    "kind": "python",
    "tests": [
        {"id": "raises", "code": "test_rejects()\n", "message": "Expect a ValueError."},
    ],
}


def test_pytest_raises_without_error_is_a_failed_check() -> None:
    """pytest.raises raises Failed, a BaseException, when nothing is raised."""
    code = (
        "import pytest\n\n"
        "def test_rejects():\n"
        "    with pytest.raises(ValueError):\n"
        "        int('1')\n"
    )
    result = check_python(CHECKER, code)
    assert not result.passed
    assert result.rule_id == "raises"
    assert "DID NOT RAISE" in result.feedback


def test_pytest_raises_with_error_passes() -> None:
    """The matching exception passes the check."""
    code = (
        "import pytest\n\n"
        "def test_rejects():\n"
        "    with pytest.raises(ValueError):\n"
        "        int('x')\n"
    )
    assert check_python(CHECKER, code).passed
