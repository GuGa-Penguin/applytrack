"""Anthropic client construction and shared AI configuration."""

from __future__ import annotations

from typing import Any

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TOKENS = 16_000
MAX_POSTING_CHARS = 60_000


class AiNotConfiguredError(RuntimeError):
    """Raised when the Anthropic SDK or its credentials are unavailable."""


class AiRequestError(RuntimeError):
    """Raised when the model call fails or returns something unusable."""


def build_client() -> Any:
    """Return an Anthropic client.

    Credentials are resolved by the SDK itself — an API key in the environment,
    or a profile written by `ant auth login`. A missing ANTHROPIC_API_KEY does
    not on its own mean there are no credentials, so we let the SDK decide.
    """
    try:
        import anthropic
    except ImportError as error:  # pragma: no cover - exercised via monkeypatch
        raise AiNotConfiguredError(
            "The anthropic package is not installed. Install it with: "
            'pip install "applytrack[ai]"'
        ) from error

    try:
        return anthropic.Anthropic()
    except Exception as error:
        raise AiNotConfiguredError(
            "Could not construct an Anthropic client. Set ANTHROPIC_API_KEY or "
            "run `ant auth login`."
        ) from error


def ensure_posting_text(text: str) -> str:
    """Validate and normalise raw posting text before sending it to the model."""
    if not isinstance(text, str):
        raise TypeError("posting text must be a string")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("posting text is empty")
    if len(cleaned) > MAX_POSTING_CHARS:
        raise ValueError(
            f"posting text exceeds {MAX_POSTING_CHARS} characters; trim it before parsing"
        )
    return cleaned
