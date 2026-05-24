"""Anthropic Claude provider — wraps the anthropic SDK."""
from __future__ import annotations

from typing import Iterator

import anthropic

from dungeon_daddy.llm.provider import LLMError, LLMMessage

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


class AnthropicProvider:
    """
    Synchronous Anthropic Claude provider.
    Thread-safe: anthropic.Anthropic is safe to share across threads.
    """

    def __init__(
        self,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        api_key: str | None = None,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            ) as stream:
                yield from stream.text_stream
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e
