"""Shared fixtures for AI output evals."""
from __future__ import annotations

import os

import pytest

from dungeon_daddy.llm.openai_provider import OpenAIProvider


@pytest.fixture(scope="module")
def provider() -> OpenAIProvider:
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — eval tests require a live API key")
    return OpenAIProvider()
