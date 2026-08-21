"""Test doubles for the Anthropic client."""

from __future__ import annotations

from types import SimpleNamespace


class FakeMessages:
    def __init__(self, parsed=None, error=None):
        self._parsed = parsed
        self._error = error
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return SimpleNamespace(parsed_output=self._parsed)


class FakeAnthropic:
    """Stands in for anthropic.Anthropic in tests."""

    def __init__(self, parsed=None, error=None):
        self.messages = FakeMessages(parsed=parsed, error=error)

    @property
    def calls(self) -> list[dict]:
        return self.messages.calls
