"""Tests for dungeon_layout.room_style — GraphRoomStyle and GraphRoomStyleResolver."""
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver

# ---------------------------------------------------------------------------
# Cycle 1 — unknown role resolves to default style
# ---------------------------------------------------------------------------

def test_unknown_role_resolves_to_default_style():
    style = GraphRoomStyleResolver().resolve("unknown")
    assert style.key == "unknown"
    assert style.priority == "low"


# ---------------------------------------------------------------------------
# Cycle 2 — boss room is high-priority with heavier border and a marker
# ---------------------------------------------------------------------------

def test_boss_room_is_high_priority_with_marker():
    style = GraphRoomStyleResolver().resolve("boss")
    assert style.key == "boss"
    assert style.priority == "high"
    assert style.border_width > 1.0
    assert style.show_marker is True
    assert style.marker_text is not None


# ---------------------------------------------------------------------------
# Cycle 5 — secret is muted (low border and fill alpha)
# ---------------------------------------------------------------------------

def test_secret_room_is_muted():
    style = GraphRoomStyleResolver().resolve("secret")
    assert style.key == "secret"
    assert style.border_alpha < 150
    assert style.fill_alpha < 30


# ---------------------------------------------------------------------------
# Cycle 6 — exit-family roles all get threshold style
# ---------------------------------------------------------------------------

import pytest


@pytest.mark.parametrize("role", ["exit", "descent", "elevator", "stairs"])
def test_exit_family_gets_threshold_style(role: str):
    style = GraphRoomStyleResolver().resolve(role)  # type: ignore[arg-type]
    assert style.key == role
    assert style.priority == "medium"
    assert style.show_marker is True


# ---------------------------------------------------------------------------
# Cycle 7 — key_room has a distinct marker
# ---------------------------------------------------------------------------

def test_key_room_has_marker():
    style = GraphRoomStyleResolver().resolve("key_room")
    assert style.key == "key_room"
    assert style.show_marker is True
    assert style.marker_text is not None


# ---------------------------------------------------------------------------
# Cycle 8 — hazard has a warning marker
# ---------------------------------------------------------------------------

def test_hazard_has_warning_marker():
    style = GraphRoomStyleResolver().resolve("hazard")
    assert style.key == "hazard"
    assert style.show_marker is True
    assert style.marker_text is not None


# ---------------------------------------------------------------------------
# Cycle 4 — hub is high-priority with size bias > 1.0
# ---------------------------------------------------------------------------

def test_hub_is_high_priority_and_larger():
    style = GraphRoomStyleResolver().resolve("hub")
    assert style.key == "hub"
    assert style.priority == "high"
    assert style.size_bias > 1.0


# ---------------------------------------------------------------------------
# Cycle 3 — entrance has a start marker
# ---------------------------------------------------------------------------

def test_entrance_has_marker():
    style = GraphRoomStyleResolver().resolve("entrance")
    assert style.key == "entrance"
    assert style.show_marker is True
    assert style.marker_text is not None


# ---------------------------------------------------------------------------
# Cycle 9 — role-specific border_color differs from unknown default
# ---------------------------------------------------------------------------

def test_entrance_border_color_differs_from_unknown():
    entrance = GraphRoomStyleResolver().resolve("entrance")
    unknown = GraphRoomStyleResolver().resolve("unknown")
    assert hasattr(entrance, "border_color")
    assert entrance.border_color != unknown.border_color


def test_hub_border_color_differs_from_unknown():
    hub = GraphRoomStyleResolver().resolve("hub")
    unknown = GraphRoomStyleResolver().resolve("unknown")
    assert hub.border_color != unknown.border_color


def test_hazard_border_color_differs_from_unknown():
    hazard = GraphRoomStyleResolver().resolve("hazard")
    unknown = GraphRoomStyleResolver().resolve("unknown")
    assert hazard.border_color != unknown.border_color


# ---------------------------------------------------------------------------
# Cycle 10 — role-specific fill_color differs from unknown default
# ---------------------------------------------------------------------------

def test_hazard_fill_color_differs_from_unknown():
    hazard = GraphRoomStyleResolver().resolve("hazard")
    unknown = GraphRoomStyleResolver().resolve("unknown")
    assert hasattr(hazard, "fill_color")
    assert hazard.fill_color != unknown.fill_color


def test_boss_fill_color_differs_from_unknown():
    boss = GraphRoomStyleResolver().resolve("boss")
    unknown = GraphRoomStyleResolver().resolve("unknown")
    assert boss.fill_color != unknown.fill_color
