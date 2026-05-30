"""Tests for dungeon_daddy.map.layout_renderer.LayoutRenderer."""
from __future__ import annotations

from unittest.mock import patch

from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import (
    LabelBox,
    LayoutBounds,
    RoomRect,
    RoutedEdge,
)
from dungeon_daddy.map.layout_renderer import LayoutRenderer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(room_id: str, x: float = 0.0, y: float = 0.0) -> RoomRect:
    return RoomRect(room_id=room_id, x=x, y=y, w=120.0, h=80.0)


def _edge(cid: str, points: list[tuple[float, float]]) -> RoutedEdge:
    return RoutedEdge(
        connection_id=cid, points=points,
        source_port="", target_port="", score=0.0,
    )


def _label(cid: str, text: str, x: float = 0.0, y: float = 0.0) -> LabelBox:
    return LabelBox(connection_id=cid, text=text, x=x, y=y, w=60.0, h=14.0)


def _result(
    rooms: dict[str, RoomRect] | None = None,
    edges: list[RoutedEdge] | None = None,
    labels: list[LabelBox] | None = None,
    room_names: dict[str, str] | None = None,
    room_roles: dict[str, str] | None = None,
    edge_labels: dict[str, str] | None = None,
    critical_path: list[str] | None = None,
) -> LayoutResult:
    r = rooms or {}
    e = edges or []
    lb = labels or []
    rn = room_names or {}
    rr = room_roles or {}
    el = edge_labels or {}
    cp = critical_path or []
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)
    return LayoutResult(
        rooms=r, edges=e, labels=lb, bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names=rn,
        room_roles=rr,  # type: ignore[arg-type]
        edge_labels=el,
        critical_path=cp,
    )


# ---------------------------------------------------------------------------
# Cycle 1 — draw() calls draw_rect_filled for each room
# ---------------------------------------------------------------------------

def test_draw_fills_each_room() -> None:
    rooms = {"a": _room("a", 0.0, 0.0), "b": _room("b", 200.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        assert mock_arcade.draw_rect_filled.call_count >= 2


# ---------------------------------------------------------------------------
# Cycle 2 — draw() calls draw_line for each edge segment
# ---------------------------------------------------------------------------

def test_draw_lines_for_each_edge_segment() -> None:
    # Edge with 3 points → 2 segments
    edges = [_edge("a→b", [(0.0, 0.0), (100.0, 0.0), (100.0, 80.0)])]
    result = _result(edges=edges)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        assert mock_arcade.draw_line.call_count >= 2


# ---------------------------------------------------------------------------
# Cycle 3 — draw() calls draw_text for labelled edges
# ---------------------------------------------------------------------------

def test_draw_text_for_labelled_edges() -> None:
    labels = [_label("a→b", "door"), _label("b→c", "passage")]
    result = _result(labels=labels)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        assert mock_arcade.draw_text.call_count >= 2


# ---------------------------------------------------------------------------
# Cycle 4 — draw() skips draw_text for empty label text
# ---------------------------------------------------------------------------

def test_draw_skips_empty_label_text() -> None:
    labels = [_label("a→b", "")]  # empty text
    result = _result(labels=labels)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        mock_arcade.draw_text.assert_not_called()


# ---------------------------------------------------------------------------
# Cycle 5 — zoom is applied to room dimensions
# ---------------------------------------------------------------------------

def test_zoom_scales_room_rect() -> None:
    rooms = {"a": _room("a", x=0.0, y=0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    calls_zoom1: list = []
    calls_zoom2: list = []

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        calls_zoom1 = list(mock_arcade.draw_rect_filled.call_args_list)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=2.0)
        calls_zoom2 = list(mock_arcade.draw_rect_filled.call_args_list)

    # The XYWH passed should differ between zoom levels
    assert calls_zoom1 != calls_zoom2


# ---------------------------------------------------------------------------
# Cycle 6 — draw() renders room name centered inside each room rect
# ---------------------------------------------------------------------------

def test_draw_text_for_room_names() -> None:
    rooms = {"a": _room("a", 0.0, 0.0), "b": _room("b", 200.0, 0.0)}
    room_names = {"a": "Entrance Hall", "b": "Guard Room"}
    result = _result(rooms=rooms, room_names=room_names)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        calls = [str(c) for c in mock_arcade.draw_text.call_args_list]
        all_text = " ".join(calls)
        assert "Entrance Hall" in all_text
        assert "Guard Room" in all_text


# ---------------------------------------------------------------------------
# Cycle 7 — selected room gets an extra teal outline
# ---------------------------------------------------------------------------

def test_selected_room_gets_teal_outline() -> None:
    from dungeon_daddy.ui.theme import TEAL
    rooms = {"a": _room("a", 0.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0, selected_room_id="a")
        colors = [call.args[1] for call in mock_arcade.draw_rect_outline.call_args_list]
        assert TEAL in colors


# ---------------------------------------------------------------------------
# Cycle 8 — room label draws room_id alongside the name (two-line display)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cycle 9 — boss room gets heavy border (border_width from style)
# ---------------------------------------------------------------------------

def test_boss_room_uses_heavy_border() -> None:
    rooms = {"boss1": _room("boss1")}
    result = _result(rooms=rooms, room_roles={"boss1": "boss"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        # boss border_width=3.0; default unknown=1.0
        widths = [call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list]
        assert 3.0 in widths


def test_unknown_room_uses_default_border() -> None:
    rooms = {"r1": _room("r1")}
    result = _result(rooms=rooms, room_roles={"r1": "unknown"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        widths = [call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list]
        assert 3.0 not in widths


# ---------------------------------------------------------------------------
# Cycle 10 — room fill alpha varies by role
# ---------------------------------------------------------------------------

def test_boss_room_has_higher_fill_alpha_than_unknown() -> None:
    boss_room = {"b": _room("b")}
    unknown_room = {"u": _room("u")}

    alpha_boss: int | None = None
    alpha_unknown: int | None = None

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer = LayoutRenderer()
        renderer.draw(_result(rooms=boss_room, room_roles={"b": "boss"}), 0.0, 0.0, 1.0)
        color = mock_arcade.draw_rect_filled.call_args_list[0].args[1]
        alpha_boss = color[3] if len(color) == 4 else None

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer = LayoutRenderer()
        renderer.draw(_result(rooms=unknown_room, room_roles={"u": "unknown"}), 0.0, 0.0, 1.0)
        color = mock_arcade.draw_rect_filled.call_args_list[0].args[1]
        alpha_unknown = color[3] if len(color) == 4 else None

    assert alpha_boss is not None and alpha_unknown is not None
    assert alpha_boss > alpha_unknown


# ---------------------------------------------------------------------------
# Cycle 11 — marked rooms draw marker text (e.g. "BOSS", "IN", "!")
# ---------------------------------------------------------------------------

def test_marked_room_draws_marker_text() -> None:
    rooms = {"b": _room("b")}
    result = _result(rooms=rooms, room_roles={"b": "boss"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        all_text = " ".join(str(c) for c in mock_arcade.draw_text.call_args_list)
        assert "BOSS" in all_text


def test_unmarked_room_omits_marker_text() -> None:
    rooms = {"u": _room("u")}
    result = _result(rooms=rooms, room_roles={"u": "unknown"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        all_text = " ".join(str(c) for c in mock_arcade.draw_text.call_args_list)
        # unknown role has show_marker=False → no marker keyword
        assert "BOSS" not in all_text and "IN" not in all_text


# ---------------------------------------------------------------------------
# Cycle 12 — secret connection uses lower alpha than normal
# ---------------------------------------------------------------------------

def test_secret_connection_uses_lower_alpha() -> None:
    edge = _edge("a→b", [(0.0, 0.0), (100.0, 0.0)])
    result = _result(edges=[edge], edge_labels={"a→b": "secret_shortcut"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        # draw_line(x1, y1, x2, y2, color, width) — color is arg[4]
        colors = [call.args[4] for call in mock_arcade.draw_line.call_args_list]
        assert any(len(c) == 4 and c[3] < 150 for c in colors)


def test_normal_connection_uses_standard_alpha() -> None:
    edge = _edge("a→b", [(0.0, 0.0), (100.0, 0.0)])
    result = _result(edges=[edge], edge_labels={"a→b": "door"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        colors = [call.args[4] for call in mock_arcade.draw_line.call_args_list]
        assert any(len(c) == 4 and c[3] >= 180 for c in colors)


# ---------------------------------------------------------------------------
# Cycle 13 — critical path rooms get an extra outline
# ---------------------------------------------------------------------------

def test_critical_path_rooms_get_extra_outline() -> None:
    rooms = {"r1": _room("r1"), "r2": _room("r2", 200.0, 0.0)}

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer = LayoutRenderer()
        renderer.draw(_result(rooms=rooms, critical_path=[]), 0.0, 0.0, 1.0)
        count_no_crit = mock_arcade.draw_rect_outline.call_count

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer = LayoutRenderer()
        renderer.draw(_result(rooms=rooms, critical_path=["r1", "r2"]), 0.0, 0.0, 1.0)
        count_with_crit = mock_arcade.draw_rect_outline.call_count

    assert count_with_crit > count_no_crit


# ---------------------------------------------------------------------------
# Cycle 14 — style_room_roles=False disables role-based border weight
# ---------------------------------------------------------------------------

def test_style_disabled_gives_default_border_for_boss() -> None:
    from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig
    rooms = {"b": _room("b")}
    result = _result(rooms=rooms, room_roles={"b": "boss"})
    config = VisualHierarchyConfig(style_room_roles=False)
    renderer = LayoutRenderer(config=config)

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        widths = [call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list]
        assert 3.0 not in widths


# ---------------------------------------------------------------------------
# Cycle 8 (original) — room label includes room_id
# ---------------------------------------------------------------------------

def test_room_label_includes_room_id() -> None:
    rooms = {"1-A": _room("1-A", 0.0, 0.0)}
    room_names = {"1-A": "Flooded Entry"}
    result = _result(rooms=rooms, room_names=room_names)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        calls = [str(c) for c in mock_arcade.draw_text.call_args_list]
        all_text = " ".join(calls)
        assert "Flooded Entry" in all_text
        assert "1-A" in all_text
