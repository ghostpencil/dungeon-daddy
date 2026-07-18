"""Wrap a raw LLM provider in the same `ObservingProvider` stack production
wires (`window.py`), so the live evals drive the real transport — including
`ObservingProvider.complete_round`, which the narrator-lookup eval is the only
test to exercise against a live provider — instead of a bare provider."""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.llm.provider import LLMProvider
from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter


def observing_eval_provider(
    inner: LLMProvider, *, agent: str, log_path: Path
) -> ObservingProvider:
    """Return `inner` wrapped exactly as the app wraps its providers."""
    return ObservingProvider(inner, agent=agent, writer=TelemetryWriter(log_path))
