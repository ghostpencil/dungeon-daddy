"""LLM observability: call records, file writer, and observing provider."""
from __future__ import annotations

import dataclasses
import datetime
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from dungeon_daddy.llm.provider import (
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRoundResult,
    LLMToolDef,
    ToolCapableProvider,
    provider_supports_tools,
)

_log = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    agent: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: float
    timestamp: str
    prompt_name: str = ""
    prompt_hash: str = ""


class TelemetryWriter:
    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path

    def record(self, record: LLMCallRecord) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(dataclasses.asdict(record), ensure_ascii=False)
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


class ObservingProvider:
    """Wraps any LLMProvider to record timing and token usage after each call."""

    def __init__(
        self,
        inner: LLMProvider,
        *,
        agent: str,
        writer: TelemetryWriter,
        prompt_name: str = "",
        prompt_hash: str = "",
    ) -> None:
        self._inner = inner
        self._agent = agent
        self._writer = writer
        self._prompt_name = prompt_name
        self._prompt_hash = prompt_hash

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def last_usage(self) -> tuple[int, int] | None:
        return self._inner.last_usage

    @property
    def supports_tools(self) -> bool:
        return provider_supports_tools(self._inner)

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> str:
        t0 = time.monotonic()
        try:
            result: str = self._inner.complete(
                messages, system=system, max_tokens=max_tokens, response_format=response_format
            )
        except Exception:
            self._record_failure((time.monotonic() - t0) * 1000)
            raise
        self._write_record((time.monotonic() - t0) * 1000)
        return result

    def complete_round(
        self,
        messages: list[LLMMessage],
        system: str = "",
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 1024,
    ) -> LLMRoundResult:
        inner = self._inner
        if not isinstance(inner, ToolCapableProvider):
            raise LLMError(
                f"{type(inner).__name__} does not support tool rounds"
            )
        t0 = time.monotonic()
        try:
            result = inner.complete_round(
                messages, system=system, tools=tools, max_tokens=max_tokens
            )
        except Exception:
            # A failed round still gets a record — otherwise failing turns are
            # invisible in the very data used to spot them.
            self._record_failure((time.monotonic() - t0) * 1000)
            raise
        self._write_record((time.monotonic() - t0) * 1000)
        return result

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        t0 = time.monotonic()
        yield from self._inner.stream(messages, system=system, max_tokens=max_tokens)
        duration_ms = (time.monotonic() - t0) * 1000
        self._write_record(duration_ms)

    def _record_failure(self, duration_ms: float) -> None:
        """Record a failed call: token counts are zeroed (the inner provider's
        ``last_usage`` only updates on success, so it is stale here), and a
        telemetry write error must not replace the in-flight provider error."""
        try:
            self._write_record(duration_ms, usage=(0, 0))
        except Exception:
            _log.exception("telemetry write failed while recording a failed LLM call")

    def _write_record(
        self, duration_ms: float, usage: tuple[int, int] | None = None
    ) -> None:
        if usage is None:
            usage = getattr(self._inner, "last_usage", None)
        prompt_tokens, completion_tokens = usage if usage else (0, 0)
        self._writer.record(LLMCallRecord(
            agent=self._agent,
            model_id=self.model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=round(duration_ms, 1),
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            prompt_name=self._prompt_name,
            prompt_hash=self._prompt_hash,
        ))
