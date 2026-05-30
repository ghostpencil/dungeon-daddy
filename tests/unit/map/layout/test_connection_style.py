"""Tests for dungeon_layout.connection_style — GraphConnectionStyle and GraphConnectionStyleResolver."""
from dungeon_daddy.map.dungeon_layout.connection_style import (
    GraphConnectionStyle,
    GraphConnectionStyleResolver,
)


# ---------------------------------------------------------------------------
# Cycle 1 — unknown/normal label resolves to default solid style
# ---------------------------------------------------------------------------

def test_unknown_label_resolves_to_default_style():
    style = GraphConnectionStyleResolver().resolve("unknown")
    assert style.key == "normal"
    assert style.dashed is False
    assert style.priority == "low"


# ---------------------------------------------------------------------------
# Cycle 2 — locked connection has thicker line and higher priority
# ---------------------------------------------------------------------------

def test_locked_connection_is_thicker_and_higher_priority():
    style = GraphConnectionStyleResolver().resolve("locked")
    assert style.key == "locked"
    assert style.line_width > 1.5
    assert style.priority == "high"
    assert style.dashed is False


# ---------------------------------------------------------------------------
# Cycle 3 — secret/shortcut connections are dashed and lower alpha
# ---------------------------------------------------------------------------

import pytest

@pytest.mark.parametrize("label", ["secret", "shortcut"])
def test_secret_and_shortcut_are_dashed_and_faint(label: str):
    style = GraphConnectionStyleResolver().resolve(label)
    assert style.key == label
    assert style.dashed is True
    assert style.alpha < 180


# ---------------------------------------------------------------------------
# Cycle 4 — vertical/hole connections have a directional marker
# ---------------------------------------------------------------------------

def test_vertical_connection_has_marker():
    style = GraphConnectionStyleResolver().resolve("vertical")
    assert style.key == "vertical"
    assert style.marker_type is not None


# ---------------------------------------------------------------------------
# Cycle 5 — hazard connection has a warning marker and medium+ priority
# ---------------------------------------------------------------------------

def test_hazard_connection_has_warning_marker():
    style = GraphConnectionStyleResolver().resolve("hazard")
    assert style.key == "hazard"
    assert style.marker_type is not None
    assert style.priority in ("medium", "high")


# ---------------------------------------------------------------------------
# Cycle 6 — impossible connection is visually distinct (dashed or faint)
# ---------------------------------------------------------------------------

def test_impossible_connection_is_visually_distinct():
    style = GraphConnectionStyleResolver().resolve("impossible")
    assert style.key == "impossible"
    normal = GraphConnectionStyleResolver().resolve("normal")
    # must differ from normal on at least one visual axis
    assert style.dashed is True or style.alpha < normal.alpha or style.line_width != normal.line_width


# ---------------------------------------------------------------------------
# Cycle 7 — dungeon JSON label aliases resolve to canonical style keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,expected_key", [
    ("hole", "vertical"),
    ("secret_shortcut", "secret"),
    ("lock_key", "locked"),
])
def test_label_aliases_resolve_to_canonical_style(label: str, expected_key: str):
    style = GraphConnectionStyleResolver().resolve(label)
    assert style.key == expected_key


def test_pursuit_resolves_to_non_standard_style():
    style = GraphConnectionStyleResolver().resolve("pursuit")
    assert style.key == "pursuit"
    normal = GraphConnectionStyleResolver().resolve("normal")
    # pursuit must be distinguishable from a plain corridor
    assert style != normal
