"""OpenAI ChatGPT provider — wraps the openai SDK."""
from __future__ import annotations

from collections.abc import Iterator

import openai

from dungeon_daddy.llm.provider import LLMError, LLMMessage

DEFAULT_OPENAI_MODEL = "gpt-4o"


class OpenAIProvider:
    """
    Synchronous OpenAI ChatGPT provider.
    Thread-safe: openai.OpenAI is safe to share across threads.
    """

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_MODEL,
        api_key: str | None = None,
    ) -> None:
        self._client = openai.OpenAI(api_key=api_key)
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
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=self._build_messages(system, messages),  # type: ignore[arg-type]
            )
            return response.choices[0].message.content or ""
        except openai.APIError as e:
            raise LLMError(str(e)) from e

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        try:
            chunks = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=self._build_messages(system, messages),  # type: ignore[arg-type]
                stream=True,
            )
            for chunk in chunks:
                delta = chunk.choices[0].delta.content  # type: ignore[union-attr]
                if delta is not None:
                    yield delta
        except openai.APIError as e:
            raise LLMError(str(e)) from e

    def _build_messages(
        self,
        system: str,
        messages: list[LLMMessage],
    ) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)
        return payload
