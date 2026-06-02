"""Tests for long_floor_framing — detection and framing for wide linear layouts."""
from dungeon_daddy.map.dungeon_layout.long_floor_framing import (
    compute_long_floor_framing_feedback,
    is_long_linear_floor,
)
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds


def _bounds(w: float, h: float) -> LayoutBounds:
    return LayoutBounds(min_x=0.0, min_y=0.0, max_x=w, max_y=h)


# ---------------------------------------------------------------------------
# Cycle 1 — Detection: wide layout is detected as long linear
# ---------------------------------------------------------------------------

def test_wide_layout_is_long_linear():
    # 600 wide × 80 tall — aspect ratio 7.5 → long linear
    assert is_long_linear_floor(_bounds(600, 80)) is True


# ---------------------------------------------------------------------------
# Cycle 2 — Detection: compact/square layout is not long linear
# ---------------------------------------------------------------------------

def test_compact_layout_is_not_long_linear():
    # 300 wide × 250 tall — aspect ratio 1.2 → not long linear
    assert is_long_linear_floor(_bounds(300, 250)) is False


def test_square_layout_is_not_long_linear():
    assert is_long_linear_floor(_bounds(200, 200)) is False


def test_tall_layout_is_not_long_linear():
    # Taller than wide
    assert is_long_linear_floor(_bounds(100, 400)) is False


# ---------------------------------------------------------------------------
# Cycle 3 — Feedback for compact floor: only is_long_linear_floor key
# ---------------------------------------------------------------------------

def test_compact_floor_feedback_minimal():
    fb = compute_long_floor_framing_feedback(_bounds(300, 250))
    assert fb["is_long_linear_floor"] is False
    # No extra keys when not long linear
    assert set(fb.keys()) == {"is_long_linear_floor"}


# ---------------------------------------------------------------------------
# Cycle 4 — Feedback for long linear floor: full fields present
# ---------------------------------------------------------------------------

def test_long_floor_feedback_has_full_fields():
    fb = compute_long_floor_framing_feedback(_bounds(600, 80))
    assert fb["is_long_linear_floor"] is True
    assert "labels_readable_after_fit" in fb
    assert "warnings" in fb
    assert isinstance(fb["warnings"], list)


def test_long_floor_feedback_readable_zoom():
    # zoom >= 0.5 → labels are readable
    fb = compute_long_floor_framing_feedback(_bounds(600, 80), fit_zoom=0.8)
    assert fb["labels_readable_after_fit"] is True


def test_long_floor_feedback_unreadable_zoom():
    # zoom < 0.5 → labels not readable, warning issued
    fb = compute_long_floor_framing_feedback(_bounds(600, 80), fit_zoom=0.3)
    assert fb["labels_readable_after_fit"] is False
    assert len(fb["warnings"]) > 0
