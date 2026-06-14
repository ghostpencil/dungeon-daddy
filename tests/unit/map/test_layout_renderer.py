"""Tests for dungeon_daddy.map.layout_renderer.LayoutRenderer."""
from __future__ import annotations

from unittest.mock import patch

from dungeon_daddy.data.models import Level, Room
from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig
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

# ---------------------------------------------------------------------------
# Cycle 15 — entrance room uses role border_color, not the fixed _ROOM_BORDER
# ---------------------------------------------------------------------------

def test_entrance_uses_role_border_color() -> None:
    from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
    entrance_style = GraphRoomStyleResolver().resolve("entrance")
    unknown_style = GraphRoomStyleResolver().resolve("unknown")

    # The two roles must have different border colors for this test to be meaningful.
    assert entrance_style.border_color != unknown_style.border_color

    entrance_rooms = {"e": _room("e")}
    unknown_rooms = {"u": _room("u")}

    def _border_colors(roles: dict[str, str], rooms: dict[str, RoomRect]) -> list[tuple]:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer = LayoutRenderer()
            renderer.draw(_result(rooms=rooms, room_roles=roles), 0.0, 0.0, 1.0)
            return [call.args[1] for call in mock_arcade.draw_rect_outline.call_args_list]

    entrance_borders = _border_colors({"e": "entrance"}, entrance_rooms)
    unknown_borders = _border_colors({"u": "unknown"}, unknown_rooms)

    # Extract the RGB component only (first 3 elements) from the first outline call
    entrance_rgb = set(c[:3] for c in entrance_borders)
    unknown_rgb = set(c[:3] for c in unknown_borders)
    assert entrance_rgb != unknown_rgb


# ---------------------------------------------------------------------------
# Cycle 16 — hazard room uses role fill_color, not the fixed _ROOM_FILL
# ---------------------------------------------------------------------------

def test_hazard_uses_role_fill_color() -> None:
    from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
    hazard_style = GraphRoomStyleResolver().resolve("hazard")
    unknown_style = GraphRoomStyleResolver().resolve("unknown")

    assert hazard_style.fill_color != unknown_style.fill_color

    hazard_rooms = {"h": _room("h")}
    unknown_rooms = {"u": _room("u")}

    def _fill_rgb(roles: dict[str, str], rooms: dict[str, RoomRect]) -> tuple:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer = LayoutRenderer()
            renderer.draw(_result(rooms=rooms, room_roles=roles), 0.0, 0.0, 1.0)
            color = mock_arcade.draw_rect_filled.call_args_list[0].args[1]
            return color[:3]

    hazard_rgb = _fill_rgb({"h": "hazard"}, hazard_rooms)
    unknown_rgb = _fill_rgb({"u": "unknown"}, unknown_rooms)
    assert hazard_rgb != unknown_rgb


# ---------------------------------------------------------------------------
# Cycle 17 — marker text is positioned near the top of the room box
# ---------------------------------------------------------------------------

def test_marker_text_is_near_top_of_room_box() -> None:
    rooms = {"e": _room("e", x=0.0, y=0.0)}   # h=80, center_y=40, top=80
    result = _result(rooms=rooms, room_roles={"e": "entrance"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, origin_x=0.0, origin_y=0.0, zoom=1.0)
        # draw_text positional args: (text, x, y, ...)
        text_calls = mock_arcade.draw_text.call_args_list
        marker_ys = [
            call.args[2]
            for call in text_calls
            if len(call.args) >= 3 and call.args[0] == "IN"
        ]
        assert marker_ys, "Marker text 'IN' was not drawn"
        # Top half: y > midpoint (wy + wh/2 = 0 + 40 = 40)
        assert all(y > 40.0 for y in marker_ys), f"Marker y={marker_ys} not near top"


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


# ---------------------------------------------------------------------------
# Cycle 18 — hovered room gets wider border than no-hover
# ---------------------------------------------------------------------------

def test_hovered_room_gets_wider_border() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"a": _room("a", 0.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    def _max_border_width() -> float:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, **extra)
            return max(call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list)

    extra: dict = {}
    width_no_hover = _max_border_width()

    extra = {"view_state": GraphViewState(hovered_room_id="a")}
    width_hovered = _max_border_width()

    assert width_hovered > width_no_hover


# ---------------------------------------------------------------------------
# Cycle 19 — clearing hover restores base border width
# ---------------------------------------------------------------------------

def test_cleared_hover_restores_base_border_width() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"a": _room("a", 0.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    def _max_width(vs: GraphViewState) -> float:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            return max(call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list)

    vs = GraphViewState(hovered_room_id="a")
    width_hovered = _max_width(vs)

    vs.hover_room(None)
    width_cleared = _max_width(vs)

    assert width_cleared < width_hovered


# ---------------------------------------------------------------------------
# Cycle 20 — hovered+selected room uses selected style, not hover-only style
# ---------------------------------------------------------------------------

def test_hovered_selected_room_uses_selected_border_color() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"a": _room("a", 0.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    # Both hover and select on same room
    vs = GraphViewState(hovered_room_id="a", selected_room_id="a")

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
        border_colors = [call.args[1] for call in mock_arcade.draw_rect_outline.call_args_list]
        # Selected border color (220, 220, 255) must appear; a pure hover-only tint would not
        assert any(c[:3] == (220, 220, 255) for c in border_colors)


# ---------------------------------------------------------------------------
# Cycle 21 — boss room hover stacks on top of heavy role border (not reset)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cycle 22 — connected room gets wider border than unrelated room when a room is selected
# ---------------------------------------------------------------------------

def test_connected_room_wider_border_than_unrelated_when_selected() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    # Rooms render in insertion order: a (selected), b (connected), c (unrelated).
    # With no critical path, each room gets exactly one draw_rect_outline call from
    # the style pass. Index 1 = b (connected), index 2 = c (unrelated).
    rooms = {
        "a": _room("a", 0.0, 0.0),
        "b": _room("b", 200.0, 0.0),
        "c": _room("c", 400.0, 0.0),
    }
    edges = [_edge("a→b", [(60.0, 40.0), (140.0, 40.0)])]
    result = _result(rooms=rooms, edges=edges)
    vs = GraphViewState(selected_room_id="a")
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
        widths = [call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list]

    # Selected room "a" now generates 3 outline calls (base + glow + second outline).
    # Room "b" (connected) and room "c" (unrelated) each get 1 call.
    # Ordering: a[0]=base, a[1]=glow, a[2]=second, b[3]=base, c[4]=base
    assert len(widths) >= 5, f"Expected ≥5 outline calls, got {len(widths)}: {widths}"
    assert widths[3] > widths[4], (
        f"Connected room b (width {widths[3]}) should be wider than "
        f"unrelated room c (width {widths[4]})"
    )


# ---------------------------------------------------------------------------
# Cycle 23 — unrelated room fades (lower border alpha) when a room is selected
# ---------------------------------------------------------------------------

def test_unrelated_room_fades_when_room_selected() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    # Single room "c" with no connection to "a".
    # Compare border alpha with vs no selection.
    rooms = {"a": _room("a", 0.0, 0.0), "c": _room("c", 400.0, 0.0)}
    result = _result(rooms=rooms)  # no edges
    renderer = LayoutRenderer()

    def _room_c_border_alpha(vs: GraphViewState | None) -> int:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            # draw_rect_outline args: (xywh, color, width)
            # color is a 4-tuple (r, g, b, a); last room = "c" → last outline call
            outline_calls = mock_arcade.draw_rect_outline.call_args_list
            # get first outline for room c (2nd room in insertion order → index 1)
            color = outline_calls[1].args[1]
            return color[3] if len(color) == 4 else 255

    alpha_no_selection = _room_c_border_alpha(None)
    alpha_with_selection = _room_c_border_alpha(GraphViewState(selected_room_id="a"))

    assert alpha_with_selection < alpha_no_selection, (
        f"Unrelated room c alpha should drop when a is selected "
        f"(no_sel={alpha_no_selection}, with_sel={alpha_with_selection})"
    )


# ---------------------------------------------------------------------------
# Cycle 24 — selected-room connections stay bright; unrelated connections fade
# ---------------------------------------------------------------------------

def test_selected_room_connections_brighter_than_unrelated_connections() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    # "a" is selected. Edge a→b is related; edge c→d is unrelated.
    rooms = {
        "a": _room("a", 0.0, 0.0),
        "b": _room("b", 200.0, 0.0),
        "c": _room("c", 400.0, 0.0),
        "d": _room("d", 600.0, 0.0),
    }
    edges = [
        _edge("a→b", [(60.0, 40.0), (140.0, 40.0)]),
        _edge("c→d", [(460.0, 40.0), (540.0, 40.0)]),
    ]
    result = _result(rooms=rooms, edges=edges)
    vs = GraphViewState(selected_room_id="a")
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
        # draw_line args: (x1, y1, x2, y2, color, width) — color[3] = alpha
        line_calls = mock_arcade.draw_line.call_args_list

    # Each edge is a single segment → 2 draw_line calls total (one per edge)
    assert len(line_calls) >= 2, f"Expected ≥2 draw_line calls, got {len(line_calls)}"
    alpha_ab = line_calls[0].args[4][3]  # a→b edge alpha
    alpha_cd = line_calls[1].args[4][3]  # c→d edge alpha

    assert alpha_ab > alpha_cd, (
        f"Edge a→b (alpha {alpha_ab}) should be brighter than unrelated c→d (alpha {alpha_cd})"
    )


# ---------------------------------------------------------------------------
# Cycle 25 — hovered connection uses higher alpha than default (no view_state)
# ---------------------------------------------------------------------------

def test_hovered_connection_uses_higher_alpha() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    edge = _edge("a→b", [(0.0, 0.0), (100.0, 0.0)])
    result = _result(edges=[edge], edge_labels={"a→b": "door"})
    renderer = LayoutRenderer()

    def _alpha(vs: GraphViewState | None) -> int:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            return mock_arcade.draw_line.call_args_list[0].args[4][3]

    alpha_default = _alpha(None)
    alpha_hovered = _alpha(GraphViewState(hovered_connection_id="a→b"))
    assert alpha_hovered > alpha_default, (
        f"Hovered connection alpha {alpha_hovered} should be > default {alpha_default}"
    )


# ---------------------------------------------------------------------------
# Cycle 26 — non-hovered connection alpha is unchanged when a different connection is hovered
# ---------------------------------------------------------------------------

def test_non_hovered_connection_alpha_unchanged() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    edges = [
        _edge("a→b", [(0.0, 0.0), (100.0, 0.0)]),
        _edge("c→d", [(200.0, 0.0), (300.0, 0.0)]),
    ]
    result = _result(edges=edges, edge_labels={"a→b": "door", "c→d": "door"})
    renderer = LayoutRenderer()

    def _alphas(vs: GraphViewState | None) -> tuple[int, int]:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            calls = mock_arcade.draw_line.call_args_list
            return calls[0].args[4][3], calls[1].args[4][3]

    alpha_ab_base, alpha_cd_base = _alphas(None)
    alpha_ab_hov, alpha_cd_hov = _alphas(GraphViewState(hovered_connection_id="a→b"))

    assert alpha_ab_hov > alpha_ab_base, "Hovered a→b should brighten"
    assert alpha_cd_hov == alpha_cd_base, "Non-hovered c→d should be unchanged"


# ---------------------------------------------------------------------------
# Cycle 27 — hovered connection gets a wider line than default
# ---------------------------------------------------------------------------

def test_hovered_connection_uses_wider_line() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    edge = _edge("a→b", [(0.0, 0.0), (100.0, 0.0)])
    result = _result(edges=[edge], edge_labels={"a→b": "door"})
    renderer = LayoutRenderer()

    def _line_width(vs: GraphViewState | None) -> float:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            return mock_arcade.draw_line.call_args_list[0].args[5]

    width_default = _line_width(None)
    width_hovered = _line_width(GraphViewState(hovered_connection_id="a→b"))
    assert width_hovered > width_default, (
        f"Hovered connection line width {width_hovered} should be > default {width_default}"
    )


def test_boss_hover_border_wider_than_boss_no_hover() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
    from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver

    boss_base_width = GraphRoomStyleResolver().resolve("boss").border_width

    rooms = {"b": _room("b", 0.0, 0.0)}
    result = _result(rooms=rooms, room_roles={"b": "boss"})
    renderer = LayoutRenderer()

    def _max_width(vs: GraphViewState | None) -> float:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            return max(call.args[2] for call in mock_arcade.draw_rect_outline.call_args_list)

    width_no_hover = _max_width(GraphViewState())
    width_hovered = _max_width(GraphViewState(hovered_room_id="b"))

    # Hover adds 1.0 on top of the boss base border_width
    assert width_hovered == boss_base_width + 1.0
    assert width_hovered > width_no_hover


# ---------------------------------------------------------------------------
# Cycle — hovered room triggers an extra draw_rect_outline call (glow)
# ---------------------------------------------------------------------------

def test_hovered_room_draws_glow_outline() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"a": _room("a", 0.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    def _outline_count(vs: GraphViewState) -> int:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            return mock_arcade.draw_rect_outline.call_count

    count_default = _outline_count(GraphViewState())
    count_hovered = _outline_count(GraphViewState(hovered_room_id="a"))
    assert count_hovered > count_default


# ---------------------------------------------------------------------------
# Cycle — selected room triggers extra draw_rect_outline calls (glow + second outline)
# ---------------------------------------------------------------------------

def test_selected_room_draws_more_outlines_than_hovered() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"a": _room("a", 0.0, 0.0)}
    result = _result(rooms=rooms)
    renderer = LayoutRenderer()

    def _outline_count(vs: GraphViewState) -> int:
        with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
            renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs)
            return mock_arcade.draw_rect_outline.call_count

    count_hovered = _outline_count(GraphViewState(hovered_room_id="a"))
    sel_state = GraphViewState()
    sel_state.select_room("a")
    count_selected = _outline_count(sel_state)
    assert count_selected > count_hovered


# ---------------------------------------------------------------------------
# Helpers for detail panel tests
# ---------------------------------------------------------------------------

def _minimal_level(room_id: str = "R1", room_name: str = "Receiving Hall") -> Level:
    room = Room(
        id=room_id, num=1, name=room_name,
        x=0, y=0, w=120, h=80, type="room", note="",
        layout_role="entrance",
    )
    return Level(
        id=1, name="Test Level", summary="", ecology="", loop="", loops=[],
        width=10, height=10, entries=[], rooms=[room], connections=[],
    )


# ---------------------------------------------------------------------------
# Cycle 28 — detail panel draws room name when room selected and level provided
# ---------------------------------------------------------------------------

def test_detail_panel_shows_room_name_when_selected() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"R1": _room("R1", 0.0, 0.0)}
    result = _result(rooms=rooms, room_names={"R1": "Receiving Hall"})
    level = _minimal_level("R1", "Receiving Hall")
    vs = GraphViewState(selected_room_id="R1")
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs, level=level)
        all_text = " ".join(str(c) for c in mock_arcade.draw_text.call_args_list)
        assert "Receiving Hall" in all_text


# ---------------------------------------------------------------------------
# Cycle 29 — detail panel suppressed when show_detail_panel=False
# ---------------------------------------------------------------------------

def test_detail_panel_suppressed_when_config_disabled() -> None:
    from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState

    rooms = {"R1": _room("R1", 0.0, 0.0)}
    result = _result(rooms=rooms, room_names={"R1": "Receiving Hall"})
    level = _minimal_level("R1", "Receiving Hall")
    vs = GraphViewState(selected_room_id="R1")
    config = GraphPresentationConfig(show_detail_panel=False)
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0, view_state=vs, level=level,
                      presentation_config=config)
        all_text = " ".join(str(c) for c in mock_arcade.draw_text.call_args_list)
        # Room name appears in the room label but NOT in a panel context;
        # check the panel-specific section header is absent
        assert "ROOM" not in all_text


# ---------------------------------------------------------------------------
# Cycle 30 — locked connection draws "LOCK" midpoint glyph
# ---------------------------------------------------------------------------

def test_locked_connection_draws_lock_glyph() -> None:
    edge = _edge("a→b", [(0.0, 0.0), (100.0, 0.0)])
    result = _result(edges=[edge], edge_labels={"a→b": "locked"})
    renderer = LayoutRenderer()

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer.draw(result, 0.0, 0.0, 1.0)
        all_text = " ".join(str(c) for c in mock_arcade.draw_text.call_args_list)
        assert "LOCK" in all_text


# ---------------------------------------------------------------------------
# Cycle 31 — secret connection uses more draw_line calls than normal (dashes)
# ---------------------------------------------------------------------------

def test_secret_connection_draws_more_lines_than_normal() -> None:
    edge = _edge("a→b", [(0.0, 0.0), (100.0, 0.0)])

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer = LayoutRenderer()
        renderer.draw(_result(edges=[edge], edge_labels={"a→b": "secret"}), 0.0, 0.0, 1.0)
        count_secret = mock_arcade.draw_line.call_count

    with patch("dungeon_daddy.map.layout_renderer.arcade") as mock_arcade:
        renderer = LayoutRenderer()
        renderer.draw(_result(edges=[edge], edge_labels={"a→b": "door"}), 0.0, 0.0, 1.0)
        count_normal = mock_arcade.draw_line.call_count

    assert count_secret > count_normal
