"""Lesson B19-L7: pass the dependency in and use a small fake."""

from __future__ import annotations

import pytest
from survey_stats.api import API, wave_count


class FakeResponse:
    """Only what wave_count uses: status_code and json()."""

    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


def test_reads_respondents_and_sends_timeout() -> None:
    calls: list[tuple[str, int]] = []

    def fake_get(url: str, timeout: int) -> FakeResponse:
        calls.append((url, timeout))
        return FakeResponse(200, {"respondents": "812"})

    assert wave_count("W14", fake_get) == 812
    assert calls == [(f"{API}/W14", 30)]


def test_raises_on_error_status() -> None:
    with pytest.raises(RuntimeError, match="503"):
        wave_count("W14", lambda url, timeout: FakeResponse(503, {}))
