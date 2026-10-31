"""Read wave metadata from the survey platform."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

API = "https://survey.example/api/waves"
TIMEOUT_SECONDS = 30


def wave_count(wave_id: str, get: Callable[..., Any]) -> int:
    """Number of respondents in one wave.

    Args:
        wave_id: Wave to look up.
        get: HTTP GET function. Production passes requests.get.

    Returns:
        The respondent count.

    Raises:
        RuntimeError: If the API does not answer with status 200.
    """
    response = get(f"{API}/{wave_id}", timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise RuntimeError(f"wave API returned {response.status_code}")
    return int(response.json()["respondents"])
