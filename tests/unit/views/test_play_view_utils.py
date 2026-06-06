"""Unit tests for play_view module-level utilities."""
from __future__ import annotations

import pytest

from dungeon_daddy.views.play_view import _wrap_debug_line


class TestWrapDebugLine:
    def test_short_line_returned_unchanged(self) -> None:
        assert _wrap_debug_line("hello", 20) == ["hello"]

    def test_exactly_max_chars_not_wrapped(self) -> None:
        line = "a" * 20
        assert _wrap_debug_line(line, 20) == [line]

    def test_simple_wrap_on_space(self) -> None:
        result = _wrap_debug_line("hello world foo bar", 12)
        assert all(len(r) <= 12 for r in result)
        assert "hello world" in result[0]

    def test_no_space_forces_hard_cut(self) -> None:
        line = "a" * 50
        result = _wrap_debug_line(line, 20)
        assert all(len(r) <= 20 for r in result)
        assert "".join(r.strip() for r in result) == line

    def test_long_clock_line_with_metadata_terminates(self) -> None:
        # Regression: long token with no spaces inside {} caused infinite loop
        line = (
            "  [0/8] The Djinn Reclaims the Engines "
            "{faction:the-crucible__desert-djinn-fragment | faction_pressure | "
            "actions: channel,focus,tinker}"
        )
        result = _wrap_debug_line(line, 36)
        assert len(result) > 1
        assert all(len(r) <= 36 for r in result)

    def test_long_room_clock_line_terminates(self) -> None:
        line = (
            "  [0/4] Scorpion Nest Agitated "
            "{room:receiving-hall | danger | actions: fight,move,endure}"
        )
        result = _wrap_debug_line(line, 36)
        assert len(result) > 1
        assert all(len(r) <= 36 for r in result)

    def test_continuation_indent_preserved(self) -> None:
        line = "  short line that wraps here because it is long enough to need wrapping"
        result = _wrap_debug_line(line, 36)
        assert len(result) >= 2
        # Continuation lines should be indented more than the original
        assert result[1].startswith("    ")
