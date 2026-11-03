"""Call Claude through the Anthropic Python SDK (anthropic 2.4.0).

The SDK is optional: install it with `pip install "anthropic>=2.4,<3"` and set
ANTHROPIC_API_KEY. Everything else in the lab runs without it, and the tests
pass a fake client instead.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
# Server-side fallback: if the model declines a request, the API retries it on a
# fallback model inside the same call. Remove both arguments to turn it off.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

CallModel = Callable[[list[dict[str, str]]], str]


def reply_text(response: Any) -> str:
    """Text of a finished reply (lesson B20-L3).

    Args:
        response: A message returned by the SDK.

    Returns:
        The first text block.

    Raises:
        RuntimeError: If the reply did not finish, or has no text block.
    """
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"reply stopped early: {response.stop_reason}")
    for block in response.content:
        if block.type == "text":
            return str(block.text)
    raise RuntimeError("reply has no text block")


def make_claude_caller(system: str, model: str = DEFAULT_MODEL, client: Any = None) -> CallModel:
    """A call_model function backed by Claude.

    Args:
        system: The system prompt.
        model: Model ID.
        client: An anthropic.Anthropic client. None builds one from the
            environment, which needs the anthropic package and an API key.

    Returns:
        A function from messages to reply text.
    """
    if client is None:
        import anthropic

        client = anthropic.Anthropic()

    def call_model(messages: list[dict[str, str]]) -> str:
        response = client.beta.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        return reply_text(response)

    return call_model
