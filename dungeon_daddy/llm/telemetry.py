"""LLM observability: call records, file writer, and observing provider."""
from __future__ import annotations

import dataclasses
import datetime
import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider


@dataclass
class LLMCallRecord:
    agent: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: float
    timestamp: str


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

    def __init__(self, inner: LLMProvider, *, agent: str, writer: TelemetryWriter) -> None:
        self._inner = inner
        self._agent = agent
        self._writer = writer

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> str:
        t0 = time.monotonic()
        result: str = self._inner.complete(
            messages, system=system, max_tokens=max_tokens, response_format=response_format
        )
        duration_ms = (time.monotonic() - t0) * 1000
        self._write_record(duration_ms)
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

    def _write_record(self, duration_ms: float) -> None:
        usage: tuple[int, int] | None = getattr(self._inner, "last_usage", None)
        prompt_tokens, completion_tokens = usage if usage else (0, 0)
        self._writer.record(LLMCallRecord(
            agent=self._agent,
            model_id=self.model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=round(duration_ms, 1),
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        ))
