"""Core LLM types: LLMMessage, LLMProvider Protocol, LLMError."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, Protocol


@dataclass
class LLMMessage:
    role: Literal["user", "assistant", "system"]
    content: str


class LLMError(Exception):
    """
    Raised by any LLMProvider implementation on API, network, or auth failure.
    Callers catch LLMError; they do not catch provider-specific exceptions.
    """


class LLMProvider(Protocol):
    """
    Synchronous LLM provider interface.
    All implementations must be safe to call from a background thread.
    """

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str: ...

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]: ...

    @property
    def model_id(self) -> str: ...
