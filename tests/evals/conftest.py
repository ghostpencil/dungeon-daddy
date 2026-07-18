"""Shared fixtures for AI output evals."""
from __future__ import annotations

import os

import pytest

from dungeon_daddy.llm.openai_provider import OpenAIProvider
from dungeon_daddy.llm.telemetry import ObservingProvider
from tests.evals.eval_provider import observing_eval_provider


@pytest.fixture(scope="module")
def provider(tmp_path_factory: pytest.TempPathFactory) -> ObservingProvider:
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — eval tests require a live API key")
    # Match production (`window.py`): every agent's provider is an
    # `ObservingProvider(OpenAIProvider(...))`, so the evals must drive that same
    # stack — otherwise `ObservingProvider.complete_round` (the tool transport the
    # narrator-lookup eval reaches) is never exercised against a live provider.
    log_path = tmp_path_factory.mktemp("eval_telemetry") / "llm_calls.jsonl"
    return observing_eval_provider(OpenAIProvider(), agent="eval", log_path=log_path)
