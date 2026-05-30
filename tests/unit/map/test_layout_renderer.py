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
) -> LayoutResult:
    r = rooms or {}
    e = edges or []
    lb = labels or []
    rn = room_names or {}
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=400.0)
    return LayoutResult(
        rooms=r, edges=e, labels=lb, bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names=rn,
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
