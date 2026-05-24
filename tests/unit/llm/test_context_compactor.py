"""Tests for ContextCompactor."""
from __future__ import annotations

import pytest

from dungeon_daddy.llm.context_compactor import ContextCompactor


def exact_counter(text: str) -> int:
    """Token counter that counts characters (deterministic for tests)."""
    return len(text)


class TestContextCompactor:
    def test_text_within_budget_returned_unchanged(self):
        compactor = ContextCompactor(count_tokens=exact_counter)
        text = "Short text."
        result = compactor.compact(text, max_tokens=100)
        assert result == text

    def test_text_over_budget_is_trimmed(self):
        compactor = ContextCompactor(count_tokens=exact_counter)
        text = "First sentence. Second sentence. Third sentence."
        result = compactor.compact(text, max_tokens=16)
        assert exact_counter(result) <= 16
        assert len(result) < len(text)

    def test_empty_text_returns_empty(self):
        compactor = ContextCompactor(count_tokens=exact_counter)
        assert compactor.compact("", max_tokens=800) == ""

    def test_default_heuristic_used_when_no_counter_provided(self):
        compactor = ContextCompactor()  # no count_tokens injected
        # 400 chars of text = 100 heuristic tokens (len//4), fits in 100 → unchanged
        text = "x" * 400
        assert compactor.compact(text, max_tokens=100) == text
        # 404 chars = 101 tokens, exceeds 100 → trimmed
        long_text = "word " * 100  # 500 chars = 125 heuristic tokens
        result = compactor.compact(long_text, max_tokens=100)
        assert len(result) < len(long_text)

    def test_section_headings_preserved_when_trimming(self):
        compactor = ContextCompactor(count_tokens=exact_counter)
        # Budget fits all headings but only some body; later heading must survive
        text = (
            "## Alpha\nThis body is too long to fit.\n\n"
            "## Beta\nShort body."
        )
        # naive trimming: stops after "## Alpha\nThis body is too long to fit." (38 chars)
        # and never reaches "## Beta" — smart trimmer must preserve it
        result = compactor.compact(text, max_tokens=35)
        assert exact_counter(result) <= 35
        assert "## Alpha" in result
        assert "## Beta" in result
