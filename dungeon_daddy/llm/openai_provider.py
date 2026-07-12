"""OpenAI ChatGPT provider — wraps the openai SDK."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import openai

from dungeon_daddy.llm.provider import (
    LLMError,
    LLMMessage,
    LLMRoundResult,
    LLMToolCall,
    LLMToolDef,
)

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
        self._last_usage: tuple[int, int] | None = None

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def last_usage(self) -> tuple[int, int] | None:
        return self._last_usage

    @property
    def supports_tools(self) -> bool:
        return True

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> str:
        try:
            built = self._build_messages(system, messages)
            if response_format is not None:
                response = self._client.chat.completions.create(  # type: ignore[call-overload]
                    model=self._model,
                    max_tokens=max_tokens,
                    messages=built,
                    response_format=response_format,
                )
            else:
                response = self._client.chat.completions.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    messages=built,  # type: ignore[arg-type]
                )
            if response.usage is not None:
                self._last_usage = (response.usage.prompt_tokens, response.usage.completion_tokens)
            return response.choices[0].message.content or ""
        except openai.APIError as e:
            raise LLMError(str(e)) from e

    def complete_round(
        self,
        messages: list[LLMMessage],
        system: str = "",
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 1024,
    ) -> LLMRoundResult:
        try:
            built = self._build_round_messages(system, messages)
            kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": built,
            }
            if tools:
                kwargs["tools"] = [_tool_def_to_openai(t) for t in tools]
            response = self._client.chat.completions.create(**kwargs)
            if response.usage is not None:
                self._last_usage = (response.usage.prompt_tokens, response.usage.completion_tokens)
            message = response.choices[0].message
            tool_calls = [
                LLMToolCall(
                    call_id=tc.id,
                    name=tc.function.name,
                    arguments=_parse_tool_arguments(tc.function.arguments),
                )
                for tc in (message.tool_calls or [])
            ]
            return LLMRoundResult(text=message.content, tool_calls=tool_calls)
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

    def _build_round_messages(
        self,
        system: str,
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        """Like ``_build_messages`` but preserves tool-use fields: assistant
        ``tool_calls`` and ``role="tool"`` results with their ``tool_call_id``."""
        payload: list[dict[str, Any]] = []
        if system:
            payload.append({"role": "system", "content": system})
        for m in messages:
            entry: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_call_id is not None:
                entry["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.call_id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            payload.append(entry)
        return payload


def _parse_tool_arguments(raw: str | None) -> dict[str, Any]:
    """Decode an OpenAI tool-call ``arguments`` JSON string. A truncated or
    malformed payload (e.g. the model hit ``max_tokens`` mid-call) is surfaced
    as ``LLMError`` — not a raw ``JSONDecodeError`` — so callers keep the
    provider contract of only ever seeing ``LLMError``."""
    try:
        return json.loads(raw or "{}")  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        raise LLMError(f"malformed tool-call arguments: {e}") from e


def _tool_def_to_openai(tool: LLMToolDef) -> dict[str, Any]:
    """Translate a provider-neutral tool def to OpenAI's function-tool format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
