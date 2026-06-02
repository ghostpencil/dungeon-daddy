"""Unit tests for connection marker resolution."""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.connection_markers import (
    ConnectionMarker,
    resolve_connection_marker,
)
from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyleResolver

_resolver = GraphConnectionStyleResolver()


def _marker(role: str) -> ConnectionMarker:
    return resolve_connection_marker(_resolver.resolve("", layout_connection_role=role))


# --- Behavior 1: locked → glyph="LOCK", not dashed ---

def test_locked_glyph():
    assert _marker("locked").midpoint_glyph == "LOCK"


def test_locked_not_dashed():
    m = _marker("locked")
    assert not m.is_dashed


# --- Behavior 2: secret → no glyph, dashed with lengths set ---

def test_secret_no_glyph():
    assert _marker("secret").midpoint_glyph is None


def test_secret_is_dashed():
    m = _marker("secret")
    assert m.is_dashed
    assert m.dash_length > 0
    assert m.gap_length > 0


# --- Behavior 3: shortcut → dashed, distinct from normal ---

def test_shortcut_is_dashed():
    assert _marker("shortcut").is_dashed


def test_shortcut_has_no_glyph():
    assert _marker("shortcut").midpoint_glyph is None


def test_normal_not_dashed():
    normal = resolve_connection_marker(_resolver.resolve(""))
    assert not normal.is_dashed


# --- Behavior 4: vertical → glyph "↕", not dashed ---

def test_vertical_glyph():
    assert _marker("vertical").midpoint_glyph == "↕"


def test_vertical_not_dashed():
    assert not _marker("vertical").is_dashed


# --- Behavior 5: critical_path / normal → no glyph, not dashed ---

def test_critical_path_no_glyph():
    assert _marker("critical_path").midpoint_glyph is None


def test_critical_path_not_dashed():
    assert not _marker("critical_path").is_dashed


# --- Behavior 6: hazard → glyph "!" ---

def test_hazard_glyph():
    assert _marker("hazard").midpoint_glyph == "!"


def test_hazard_not_dashed():
    assert not _marker("hazard").is_dashed
