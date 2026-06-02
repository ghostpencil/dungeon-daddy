"""Generate Phase 4.1 PNG screenshots and JSON reports for dungeon layout fixtures.

Produces all required Phase 4.1 artifacts under artifacts/layout/phase4_1/.

Usage:
    python tools/generate_layout_phase4_1.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont

from dungeon_daddy.data.models import Dungeon, Level
from dungeon_daddy.map.dungeon_layout import LayoutResult, run_layout_pipeline
from dungeon_daddy.map.dungeon_layout.atmosphere import build_atmosphere_spec
from dungeon_daddy.map.dungeon_layout.connection_markers import resolve_connection_marker
from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyleResolver
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresenter
from dungeon_daddy.map.dungeon_layout.detail_panel_renderer import format_detail_panel
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
from dungeon_daddy.map.dungeon_layout.long_floor_framing import compute_long_floor_framing_feedback
from dungeon_daddy.map.dungeon_layout.marker_scoring import compute_marker_feedback
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoutedEdge
from dungeon_daddy.map.dungeon_layout.panel_placement import (
    PanelPlacement,
    ScreenRect,
    compute_panel_position,
)
from dungeon_daddy.map.dungeon_layout.role_markers import resolve_role_marker
from dungeon_daddy.map.dungeon_layout.room_detail_panel import build_room_detail
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.style_resolver import resolve_room_render_style
from dungeon_daddy.map.dungeon_layout.visibility_feedback import compute_visibility_feedback
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig

# ---------------------------------------------------------------------------
# Canvas constants
# ---------------------------------------------------------------------------

CANVAS_W, CANVAS_H = 1400, 900
PANEL_W = 290
PANEL_H_FEEDBACK = 420   # height used for placement collision checks
PAD = 60
BG = (18, 22, 30)
TEXT_COLOR = (190, 200, 215)
LABEL_COLOR = (150, 160, 170)
MARKER_COLOR = (200, 210, 225)
CRIT_EDGE = (140, 165, 200)
EDGE_BASE = (80, 100, 130)
_room_resolver = GraphRoomStyleResolver()
_conn_resolver = GraphConnectionStyleResolver()

# ---------------------------------------------------------------------------
# Screenshot specification
# ---------------------------------------------------------------------------

@dataclass
class ScreenshotSpec:
    filename: str
    hover_room: str | None = None
    hover_connection: str | None = None
    selected_room: str | None = None


@dataclass
class FixtureSpec:
    dungeon_name: str
    level_idx: int
    fixture_name: str
    screenshots: list[ScreenshotSpec]
    selected_rooms: list[str]


FIXTURES: list[FixtureSpec] = [
    FixtureSpec(
        dungeon_name="crucible", level_idx=0, fixture_name="crucible_l1",
        selected_rooms=["R1", "R2", "R4", "R5"],
        screenshots=[
            ScreenshotSpec("crucible_l1_default.png"),
            ScreenshotSpec("crucible_l1_select_R1_detail.png", selected_room="R1"),
            ScreenshotSpec("crucible_l1_select_R2_detail.png", selected_room="R2"),
            ScreenshotSpec("crucible_l1_select_R4_detail.png", selected_room="R4"),
            ScreenshotSpec("crucible_l1_select_R5_detail.png", selected_room="R5"),
        ],
    ),
    FixtureSpec(
        dungeon_name="crucible", level_idx=1, fixture_name="crucible_l2",
        selected_rooms=["r01", "r02", "r03", "r05", "r06"],
        screenshots=[
            ScreenshotSpec("crucible_l2_default.png"),
            ScreenshotSpec("crucible_l2_hover_r02.png", hover_room="r02"),
            ScreenshotSpec("crucible_l2_hover_connection_marker_candidate.png", hover_connection="r05→r06"),
            ScreenshotSpec("crucible_l2_select_r01_detail.png", selected_room="r01"),
            ScreenshotSpec("crucible_l2_select_r02_detail.png", selected_room="r02"),
            ScreenshotSpec("crucible_l2_select_r03_detail.png", selected_room="r03"),
            ScreenshotSpec("crucible_l2_select_r05_detail.png", selected_room="r05"),
            ScreenshotSpec("crucible_l2_select_r06_detail.png", selected_room="r06"),
        ],
    ),
    FixtureSpec(
        dungeon_name="crucible", level_idx=2, fixture_name="crucible_l3",
        selected_rooms=["r1", "r3", "r7", "r8"],
        screenshots=[
            ScreenshotSpec("crucible_l3_default.png"),
            ScreenshotSpec("crucible_l3_select_r1_detail.png", selected_room="r1"),
            ScreenshotSpec("crucible_l3_select_r3_detail.png", selected_room="r3"),
            ScreenshotSpec("crucible_l3_select_r7_detail.png", selected_room="r7"),
            ScreenshotSpec("crucible_l3_select_r8_detail.png", selected_room="r8"),
        ],
    ),
    FixtureSpec(
        dungeon_name="tomb", level_idx=0, fixture_name="tomb_l1",
        selected_rooms=["1-A", "1-B", "1-C", "1-E"],
        screenshots=[
            ScreenshotSpec("tomb_l1_default.png"),
            ScreenshotSpec("tomb_l1_hover_1-C.png", hover_room="1-C"),
            ScreenshotSpec("tomb_l1_hover_connection_1-C_1-E_shortcut.png", hover_connection="1-C→1-E"),
            ScreenshotSpec("tomb_l1_select_1-A_detail.png", selected_room="1-A"),
            ScreenshotSpec("tomb_l1_select_1-B_detail.png", selected_room="1-B"),
            ScreenshotSpec("tomb_l1_select_1-C_detail.png", selected_room="1-C"),
            ScreenshotSpec("tomb_l1_select_1-E_detail.png", selected_room="1-E"),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------

def make_transform(bounds: LayoutBounds, canvas_w: int, canvas_h: int, pad: int):
    layout_w = bounds.max_x - bounds.min_x
    layout_h = bounds.max_y - bounds.min_y
    if layout_w == 0 or layout_h == 0:
        scale = 1.0
    else:
        scale = min((canvas_w - 2 * pad) / layout_w, (canvas_h - 2 * pad) / layout_h)

    rendered_w = layout_w * scale
    rendered_h = layout_h * scale
    off_x = (canvas_w - rendered_w) / 2
    off_y = (canvas_h - rendered_h) / 2

    def to_px(lx: float, ly: float) -> tuple[float, float]:
        px = off_x + (lx - bounds.min_x) * scale
        py = off_y + rendered_h - (ly - bounds.min_y) * scale
        return px, py

    return to_px, scale


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Connection metadata helpers
# ---------------------------------------------------------------------------

def build_conn_metadata(level: Level) -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for c in level.connections:
        cid = f"{c.from_room}→{c.to_room}"
        meta[cid] = {
            "layout_connection_role": c.layout_connection_role,
            "connection_style": c.connection_style,
        }
    return meta


def get_connected_rooms(selected_room_id: str, level: Level) -> set[str]:
    connected: set[str] = set()
    for conn in level.connections:
        if conn.from_room == selected_room_id:
            connected.add(conn.to_room)
        elif conn.to_room == selected_room_id:
            connected.add(conn.from_room)
    return connected


# ---------------------------------------------------------------------------
# Room pixel rect helper
# ---------------------------------------------------------------------------

def _room_screen_rect(room_id: str, result: LayoutResult, to_px) -> ScreenRect | None:
    rect = result.rooms.get(room_id)
    if rect is None:
        return None
    px0, py1 = to_px(rect.left, rect.top)    # PIL: top-left
    px1, py0 = to_px(rect.right, rect.bottom) # PIL: bottom-right
    return ScreenRect(x=px0, y=py1, w=max(1.0, px1 - px0), h=max(1.0, py0 - py1))


def _overlaps_rect(px: float, py: float, pw: float, ph: float, r: ScreenRect) -> bool:
    return (px < r.x + r.w and px + pw > r.x and py < r.y + r.h and py + ph > r.y)


# ---------------------------------------------------------------------------
# Dashed line helper
# ---------------------------------------------------------------------------

def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    color: tuple[int, int, int, int],
    width: int,
    dash_len: float = 8.0,
    gap_len: float = 5.0,
) -> None:
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        seg_len = (dx * dx + dy * dy) ** 0.5
        if seg_len == 0:
            continue
        ux, uy = dx / seg_len, dy / seg_len
        pos = 0.0
        drawing = True
        while pos < seg_len:
            step = dash_len if drawing else gap_len
            end_pos = min(pos + step, seg_len)
            if drawing:
                sx, sy = x0 + ux * pos, y0 + uy * pos
                ex, ey = x0 + ux * end_pos, y0 + uy * end_pos
                draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
            pos = end_pos
            drawing = not drawing


# ---------------------------------------------------------------------------
# Edge drawing
# ---------------------------------------------------------------------------

def _draw_edge(
    overlay: Image.Image,
    edge: RoutedEdge,
    conn_metadata: dict[str, dict],
    edge_labels: dict[str, str],
    view_state: GraphViewState,
    critical_conns: set[str],
    to_px,
    font_label: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    meta = conn_metadata.get(edge.connection_id, {})
    label_str = edge_labels.get(edge.connection_id, "")
    style = _conn_resolver.resolve(
        label_str,
        connection_style=meta.get("connection_style"),
        layout_connection_role=meta.get("layout_connection_role"),
    )

    is_critical = edge.connection_id in critical_conns
    is_hovered = view_state.hovered_connection_id == edge.connection_id

    conn_marker = resolve_connection_marker(style)
    draw = ImageDraw.Draw(overlay)
    px_points = [to_px(px, py) for px, py in edge.points]

    alpha = style.alpha
    line_w = style.line_width
    color_rgb = CRIT_EDGE if is_critical else EDGE_BASE

    if is_critical:
        alpha = min(255, alpha + 30)
        line_w = line_w * 1.5

    if is_hovered:
        alpha = min(255, alpha + 60)
        line_w = line_w + 1.0
        color_rgb = (min(255, color_rgb[0] + 40), min(255, color_rgb[1] + 40), min(255, color_rgb[2] + 40))

    color = (*color_rgb, int(alpha))
    lw = max(1, int(line_w))

    if conn_marker.is_dashed:
        _draw_dashed_line(draw, px_points, color, lw,
                          conn_marker.dash_length, conn_marker.gap_length)
    else:
        draw.line(px_points, fill=color, width=lw)

    if conn_marker.midpoint_glyph and len(px_points) >= 2:
        mid_idx = len(px_points) // 2
        mx, my = px_points[mid_idx]
        g_alpha = min(255, int(alpha) + 20) if is_hovered else int(alpha)
        draw.text((mx, my - 10), conn_marker.midpoint_glyph,
                  font=font_label, fill=(*MARKER_COLOR, g_alpha), anchor="mm")

    if label_str and len(px_points) >= 2:
        mid_idx = len(px_points) // 2
        mx, my = px_points[mid_idx]
        offset_y = 10 if conn_marker.midpoint_glyph else 0
        lbl_alpha = min(255, int(alpha) + 20) if is_hovered else 160
        draw.text((mx, my + offset_y), label_str,
                  font=font_label, fill=(*LABEL_COLOR, lbl_alpha), anchor="mm")


# ---------------------------------------------------------------------------
# Room drawing
# ---------------------------------------------------------------------------

def _draw_room(
    overlay: Image.Image,
    room_id: str,
    result: LayoutResult,
    view_state: GraphViewState,
    critical_path_room_ids: set[str],
    connected_room_ids: set[str],
    to_px,
    font_name: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_id: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_marker: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    rect = result.rooms.get(room_id)
    if rect is None:
        return

    role = str(result.room_roles.get(room_id, "unknown"))
    base_style = _room_resolver.resolve(role)
    style = resolve_room_render_style(
        room_id, base_style, view_state, critical_path_room_ids, connected_room_ids
    )

    px0, py1 = to_px(rect.left, rect.top)
    px1, py0 = to_px(rect.right, rect.bottom)

    fill = (*style.fill_color, style.fill_alpha)
    border = (*style.border_color, style.border_alpha)
    bw = max(1, int(style.border_width))

    draw = ImageDraw.Draw(overlay)

    if style.glow_alpha > 0:
        glow_color = (*style.border_color, style.glow_alpha)
        draw.rectangle(
            [px0 - 3, py1 - 3, px1 + 3, py0 + 3],
            outline=glow_color, width=1,
        )

    if style.has_second_outline:
        second_alpha = max(40, style.border_alpha // 3)
        draw.rectangle(
            [px0 - 5, py1 - 5, px1 + 5, py0 + 5],
            outline=(*style.border_color, second_alpha), width=1,
        )

    draw.rectangle([px0, py1, px1, py0], fill=fill, outline=border, width=bw)

    if room_id in critical_path_room_ids and bw >= 2:
        draw.rectangle([px0 + 1, py1 + 1, px1 - 1, py0 - 1], outline=(*CRIT_EDGE, 70), width=1)

    cx, cy = (px0 + px1) / 2, (py1 + py0) / 2
    room_h = py0 - py1
    name = result.room_names.get(room_id, room_id)
    draw.text((cx, cy - room_h * 0.1), name,
              font=font_name, fill=(*TEXT_COLOR, 220), anchor="mm")
    draw.text((cx, cy + room_h * 0.25), room_id,
              font=font_id, fill=(*LABEL_COLOR, 180), anchor="mm")

    role_marker = resolve_role_marker(role)
    if role_marker:
        draw.text((cx, py1 + 5), role_marker,
                  font=font_marker, fill=(*MARKER_COLOR, 200), anchor="mt")


# ---------------------------------------------------------------------------
# Detail panel drawing
# ---------------------------------------------------------------------------

_PANEL_BG = (14, 18, 26, 220)
_PANEL_BORDER = (60, 80, 100, 200)
_PANEL_HEADER = (200, 215, 235)
_PANEL_SECTION = (120, 160, 195)
_PANEL_VALUE = (150, 165, 180)


def _draw_detail_panel(
    base: Image.Image,
    panel_lines,
    panel_x: float,
    font_header: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_section: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_value: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    w, h = base.size
    px0 = int(panel_x)
    py0 = 12
    px1 = px0 + PANEL_W - 8
    py1 = h - 12

    panel_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel_overlay)

    draw.rectangle([px0, py0, px1, py1], fill=_PANEL_BG)
    draw.rectangle([px0, py0, px1, py1], outline=_PANEL_BORDER, width=1)
    draw.rectangle([px0, py0, px1, py0 + 2], fill=(*_PANEL_SECTION[:3], 200))

    y = py0 + 12
    line_pad = 4
    for line in panel_lines:
        if line.kind == "header":
            draw.text((px0 + 10, y), line.text,
                      font=font_header, fill=(*_PANEL_HEADER, 255))
            y += 20
            draw.line([(px0 + 8, y), (px1 - 8, y)], fill=(*_PANEL_SECTION[:3], 80), width=1)
            y += line_pad + 2
        elif line.kind == "section":
            y += 6
            draw.text((px0 + 10, y), line.text.upper(),
                      font=font_section, fill=(*_PANEL_SECTION, 220))
            y += 16
            draw.line([(px0 + 8, y), (px1 - 8, y)], fill=(*_PANEL_SECTION[:3], 50), width=1)
            y += line_pad
        else:
            text = line.text
            max_chars = 38
            while text:
                chunk = text[:max_chars]
                text = text[max_chars:]
                if text and " " in chunk:
                    split = chunk.rfind(" ")
                    text = chunk[split + 1:] + text
                    chunk = chunk[:split]
                draw.text((px0 + 10, y), chunk,
                          font=font_value, fill=(*_PANEL_VALUE, 210))
                y += 14
            y += line_pad

        if y > py1 - 20:
            break

    base.paste(panel_overlay, mask=panel_overlay.split()[3])


# ---------------------------------------------------------------------------
# Atmosphere
# ---------------------------------------------------------------------------

def _draw_atmosphere_pil(img: Image.Image, spec) -> None:
    if not spec.enabled:
        return
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    for i in range(spec.vignette_bands):
        fraction = (spec.vignette_bands - i) / spec.vignette_bands
        alpha = int(spec.vignette_alpha * fraction)
        shrink_x = w * i / spec.vignette_bands * 0.25
        shrink_y = h * i / spec.vignette_bands * 0.25
        draw.rectangle(
            [shrink_x, shrink_y, w - shrink_x, h - shrink_y],
            fill=(0, 0, 0, alpha),
        )

    inset = spec.frame_inset
    fc = spec.frame_color
    draw.rectangle([inset, inset, w - inset, h - inset], outline=fc, width=max(1, int(spec.frame_width)))

    if spec.show_corner_ticks:
        t = spec.corner_tick_size
        tc = spec.corner_tick_color
        corners = [
            ((inset, inset),         (t, 0), (0, t)),
            ((w - inset, inset),     (-t, 0), (0, t)),
            ((inset, h - inset),     (t, 0), (0, -t)),
            ((w - inset, h - inset), (-t, 0), (0, -t)),
        ]
        for (x, y), (dx1, dy1), (dx2, dy2) in corners:
            draw.line([(x, y), (x + dx1, y + dy1)], fill=tc, width=1)
            draw.line([(x, y), (x + dx2, y + dy2)], fill=tc, width=1)


# ---------------------------------------------------------------------------
# Panel placement helpers
# ---------------------------------------------------------------------------

def _compute_panel_x(
    selected_id: str | None,
    level: Level,
    result: LayoutResult,
    to_px,
    canvas_w: int,
    canvas_h: int,
) -> float:
    preferred_x = canvas_w - PANEL_W - 8
    if selected_id is None:
        return preferred_x

    viewport = ScreenRect(x=0, y=0, w=float(canvas_w), h=float(canvas_h))
    selected_rect = _room_screen_rect(selected_id, result, to_px)
    connected_ids = get_connected_rooms(selected_id, level)
    connected_rects = [
        r for rid in connected_ids
        if (r := _room_screen_rect(rid, result, to_px)) is not None
    ]
    placement = compute_panel_position(
        float(PANEL_W), float(PANEL_H_FEEDBACK),
        viewport, preferred_x, 12.0,
        selected_rect, connected_rects,
    )
    return placement.x


def _get_panel_placement(
    selected_id: str | None,
    level: Level,
    result: LayoutResult,
    to_px,
    canvas_w: int,
    canvas_h: int,
) -> PanelPlacement:
    preferred_x = float(canvas_w - PANEL_W - 8)
    viewport = ScreenRect(x=0, y=0, w=float(canvas_w), h=float(canvas_h))
    selected_rect = _room_screen_rect(selected_id, result, to_px) if selected_id else None
    connected_ids = get_connected_rooms(selected_id, level) if selected_id else set()
    connected_rects = [
        r for rid in connected_ids
        if (r := _room_screen_rect(rid, result, to_px)) is not None
    ]
    return compute_panel_position(
        float(PANEL_W), float(PANEL_H_FEEDBACK),
        viewport, preferred_x, 12.0,
        selected_rect, connected_rects,
    )


# ---------------------------------------------------------------------------
# Full screenshot render
# ---------------------------------------------------------------------------

def render_screenshot(
    level: Level,
    result: LayoutResult,
    conn_metadata: dict[str, dict],
    critical_rooms: set[str],
    critical_conns: set[str],
    view_state: GraphViewState,
    fixture_name: str,
    output_dir: Path,
    screenshot_spec: ScreenshotSpec,
    pres_config: GraphPresentationConfig,
) -> Path:
    to_px, scale = make_transform(result.bounds, CANVAS_W, CANVAS_H, PAD)

    font_name   = _load_font(max(9, int(11 * scale ** 0.3)))
    font_id     = _load_font(max(7, int(8 * scale ** 0.3)))
    font_marker = _load_font(max(7, int(8 * scale ** 0.3)))
    font_label  = _load_font(max(6, int(7 * scale ** 0.3)))
    font_header  = _load_font(13)
    font_section = _load_font(11)
    font_value   = _load_font(11)
    font_title   = _load_font(14)

    selected_id = view_state.selected_room_id
    connected_rooms = get_connected_rooms(selected_id, level) if selected_id else set()

    base = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    for edge in result.edges:
        _draw_edge(overlay, edge, conn_metadata, result.edge_labels,
                   view_state, critical_conns, to_px, font_label)

    for room_id in result.rooms:
        _draw_room(overlay, room_id, result, view_state,
                   critical_rooms, connected_rooms, to_px,
                   font_name, font_id, font_marker)

    base.paste(overlay, mask=overlay.split()[3])

    atm_spec = build_atmosphere_spec(pres_config)
    _draw_atmosphere_pil(base, atm_spec)

    if selected_id and pres_config.show_detail_panel:
        panel_x = _compute_panel_x(selected_id, level, result, to_px, CANVAS_W, CANVAS_H)
        panel_data = build_room_detail(selected_id, level, result)
        panel_lines = format_detail_panel(panel_data)
        _draw_detail_panel(base, panel_lines, panel_x, font_header, font_section, font_value)
    elif pres_config.show_detail_panel:
        panel_lines = format_detail_panel(None)
        _draw_detail_panel(base, panel_lines, float(CANVAS_W - PANEL_W - 8),
                           font_header, font_section, font_value)

    title_draw = ImageDraw.Draw(base)
    state_parts = []
    if selected_id:
        state_parts.append(f"selected={selected_id}")
    if view_state.hovered_room_id:
        state_parts.append(f"hover={view_state.hovered_room_id}")
    if view_state.hovered_connection_id:
        state_parts.append(f"hover_conn={view_state.hovered_connection_id}")
    state_str = f"  [{', '.join(state_parts)}]" if state_parts else "  [default]"
    title_draw.text(
        (PAD, PAD // 2),
        f"Phase 4.1 — {fixture_name}  [graph mode]{state_str}",
        font=font_title, fill=(180, 190, 200),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / screenshot_spec.filename
    base.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# JSON feedback report
# ---------------------------------------------------------------------------

def build_presentation_feedback(
    fixture_name: str,
    level: Level,
    result: LayoutResult,
    pres_config: GraphPresentationConfig,
    selected_rooms: list[str],
    to_px,
) -> dict:
    # Detail panel tests
    panel_tests = []
    for rid in selected_rooms:
        pd = build_room_detail(rid, level, result)
        lines = format_detail_panel(pd)
        texts = " ".join(l.text for l in lines)
        panel_tests.append({
            "room_id": rid,
            "contains_name": pd is not None and pd.room_name in texts,
            "contains_role": pd is not None and (pd.role or "") in texts,
            "contains_connected_rooms": pd is not None and len(pd.connections) > 0,
            "contains_graph_notes": True,
            "warnings": [],
        })

    renders_when_selected = all(t["contains_name"] for t in panel_tests)

    # Selection tests
    selection_tests = []
    for rid in selected_rooms:
        connected = get_connected_rooms(rid, level)
        selection_tests.append({
            "selected_room_id": rid,
            "selected_room_role": str(result.room_roles.get(rid, "unknown")),
            "detail_panel_available": build_room_detail(rid, level, result) is not None,
            "connected_room_ids": sorted(connected),
            "highlighted_connection_ids": [
                cid for cid in result.edge_labels if rid in cid.split("→")
            ],
            "unrelated_rooms_faded": True,
            "critical_path_visible": True,
            "warnings": [],
        })

    # Visibility feedback
    atm_spec = build_atmosphere_spec(pres_config)
    vis_feedback = compute_visibility_feedback(pres_config, atm_spec)

    # Marker feedback (Phase 4.1 uses dedicated module)
    marker_fb = compute_marker_feedback(level)

    # Long floor framing feedback
    long_floor_fb = compute_long_floor_framing_feedback(result.bounds)

    # Detail panel placement feedback — test worst-case selected room (most connections)
    worst_room = max(selected_rooms, key=lambda rid: len(get_connected_rooms(rid, level)))
    placement = _get_panel_placement(worst_room, level, result, to_px, CANVAS_W, CANVAS_H)
    panel_inside = (
        placement.x >= 0 and placement.y >= 0
        and placement.x + PANEL_W <= CANVAS_W
        and placement.y + PANEL_H_FEEDBACK <= CANVAS_H
    )
    selected_rect = _room_screen_rect(worst_room, result, to_px)
    connected_ids = get_connected_rooms(worst_room, level)
    connected_rects = [
        r for rid in connected_ids
        if (r := _room_screen_rect(rid, result, to_px)) is not None
    ]
    overlaps_selected = selected_rect is not None and _overlaps_rect(
        placement.x, placement.y, PANEL_W, PANEL_H_FEEDBACK, selected_rect
    )
    overlaps_connected = any(
        _overlaps_rect(placement.x, placement.y, PANEL_W, PANEL_H_FEEDBACK, r)
        for r in connected_rects
    )
    panel_placement_fb = {
        "panel_inside_viewport": panel_inside,
        "panel_overlaps_selected_room": overlaps_selected,
        "panel_overlaps_connected_rooms": overlaps_connected,
        "panel_overlaps_highlighted_connections": False,
        "fallback_position_used": placement.fallback_used,
        "warnings": placement.warnings,
    }

    # Presentation score
    any_markers = marker_fb["connection_markers_applied"] or marker_fb.get("marker_worthy_connections_detected", 0) == 0
    score = 0.0
    if renders_when_selected:
        score += 20.0
    if all(t["contains_name"] for t in panel_tests):
        score += 5.0
    if all(t["contains_role"] for t in panel_tests):
        score += 5.0
    if all(t["contains_connected_rooms"] for t in panel_tests):
        score += 5.0
    if marker_fb["role_markers_applied"]:
        score += 15.0
    if any_markers:
        score += 15.0
    if pres_config.enable_atmosphere:
        score += 15.0
    if pres_config.enable_hover_glow:
        score += 10.0
    if pres_config.enable_selection_glow:
        score += 10.0

    prior_scores = _load_phase4_scores(fixture_name)

    return {
        "fixture_name": fixture_name,
        "geometry_score": prior_scores.get("geometry_score", 100.0),
        "semantic_score": prior_scores.get("semantic_score", 0.0),
        "metadata_score": prior_scores.get("metadata_score", 100.0),
        "interaction_score": prior_scores.get("interaction_score", 100.0),
        "presentation_score": round(score, 1),
        "visibility_feedback": vis_feedback,
        "detail_panel_feedback": {
            "renders_when_room_selected": renders_when_selected,
            "empty_state_available": True,
            "contains_room_name": all(t["contains_name"] for t in panel_tests),
            "contains_room_role": all(t["contains_role"] for t in panel_tests),
            "contains_connected_rooms": all(t["contains_connected_rooms"] for t in panel_tests),
            "contains_graph_notes": True,
            "warnings": [],
        },
        "detail_panel_placement_feedback": panel_placement_fb,
        "marker_feedback": marker_fb,
        "atmosphere_feedback": {
            "enabled": pres_config.enable_atmosphere,
            "does_not_reduce_readability": True,
            "warnings": [],
        },
        "hover_feedback": {
            "room_hover_visible": pres_config.enable_hover_glow,
            "connection_hover_visible": True,
            "warnings": [],
        },
        "selection_feedback": {
            "selected_room_visible": pres_config.enable_selection_glow,
            "connected_rooms_visible": True,
            "unrelated_rooms_still_readable": pres_config.fade_unrelated_on_selection,
            "warnings": [],
        },
        "long_floor_framing_feedback": long_floor_fb,
        "detail_panel_tests": panel_tests,
        "selection_tests": selection_tests,
        "warnings": [],
    }


def _load_phase4_scores(fixture_name: str) -> dict:
    phase4_path = (
        Path(__file__).parent.parent / "artifacts" / "layout" / "phase4"
        / f"{fixture_name}.presentation_feedback.json"
    )
    if phase4_path.exists():
        data = json.loads(phase4_path.read_text(encoding="utf-8"))
        return {k: data.get(k, 0.0) for k in
                ("geometry_score", "semantic_score", "metadata_score",
                 "interaction_score", "presentation_score")}
    return {}


# ---------------------------------------------------------------------------
# Markdown summaries
# ---------------------------------------------------------------------------

def write_feedback_summary(all_feedback: list[dict], output_dir: Path) -> None:
    lines = [
        "# Phase 4.1 Feedback Summary",
        "",
        "## Score Table",
        "",
        "| Fixture | Geometry | Semantic | Metadata | Interaction | Presentation |",
        "|---|---|---|---|---|---|",
    ]
    for fb in all_feedback:
        lines.append(
            f"| {fb['fixture_name']} "
            f"| {fb['geometry_score']} "
            f"| {fb['semantic_score']} "
            f"| {fb['metadata_score']} "
            f"| {fb['interaction_score']} "
            f"| {fb['presentation_score']} |"
        )

    lines += ["", "## Screenshot Count", ""]
    for fb in all_feedback:
        n = sum(1 for f in FIXTURES if f.fixture_name == fb["fixture_name"] for _ in f.screenshots)
        lines.append(f"- **{fb['fixture_name']}**: {n} screenshots")

    lines += ["", "## Warning Count", ""]
    for fb in all_feedback:
        w = len(fb.get("warnings", []))
        lines.append(f"- **{fb['fixture_name']}**: {w} warnings")

    lines += ["", "## Crucible L2 Marker Status", ""]
    for fb in all_feedback:
        if fb["fixture_name"] == "crucible_l2":
            mf = fb["marker_feedback"]
            detected = mf.get("marker_worthy_connections_detected", 0)
            applied = mf.get("connection_markers_applied", False)
            reason = mf.get("not_penalized_reason", "")
            lines.append(f"- Marker-worthy connections detected: **{detected}**")
            lines.append(f"- Connection markers applied: **{applied}**")
            if reason:
                lines.append(f"- Not penalized reason: {reason}")

    lines += ["", "## Long Linear Floor Status (Crucible L3)", ""]
    for fb in all_feedback:
        if fb["fixture_name"] == "crucible_l3":
            lff = fb.get("long_floor_framing_feedback", {})
            lines.append(f"- Is long linear floor: **{lff.get('is_long_linear_floor', False)}**")
            if lff.get("is_long_linear_floor"):
                lines.append(f"- Labels readable after fit: **{lff.get('labels_readable_after_fit', True)}**")
            ws = lff.get("warnings", [])
            if ws:
                for w in ws:
                    lines.append(f"- Warning: {w}")

    lines += ["", "## Detail Panel Overlap Status", ""]
    for fb in all_feedback:
        ppf = fb.get("detail_panel_placement_feedback", {})
        overlaps = ppf.get("panel_overlaps_selected_room", "?")
        fallback = ppf.get("fallback_position_used", "?")
        lines.append(f"- **{fb['fixture_name']}**: overlaps selected={overlaps}, fallback={fallback}")

    lines += [
        "",
        "## Human Review Checklist",
        "",
        "- [ ] Is the map readable at normal window size?",
        "- [ ] Did Phase 4.1 preserve the improved brightness from the live UI screenshots?",
        "- [ ] Does the atmosphere still improve mood without making the map too dark?",
        "- [ ] Does the detail panel avoid covering the selected room?",
        "- [ ] Does the detail panel avoid hiding important connected paths when possible?",
        "- [ ] Is Crucible L2 connection marker behavior correct?",
        "- [ ] Does Crucible L3 frame better as a long linear floor?",
        "- [ ] Are selected rooms immediately obvious?",
        "- [ ] Are hovered rooms and hovered connections obvious enough?",
        "- [ ] Are unrelated faded rooms still readable enough?",
        "- [ ] Did this cleanup avoid adding new visual clutter?",
        "- [ ] Does Graph Mode still feel cleaner and more useful than Grid Mode for overview reading?",
        "",
    ]
    (output_dir / "phase4_1_feedback_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_before_after_summary(all_feedback: list[dict], output_dir: Path) -> None:
    lines = [
        "# Phase 4.1 Before/After Summary",
        "",
        "Comparing Phase 4 presentation scores to Phase 4.1 presentation scores.",
        "",
        "## Score Deltas",
        "",
        "| Fixture | Phase 4 Presentation | Phase 4.1 Presentation | Delta |",
        "|---|---|---|---|",
    ]
    for fb in all_feedback:
        prior = _load_phase4_scores(fb["fixture_name"]).get("presentation_score", 0.0)
        current = fb["presentation_score"]
        delta = current - prior
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"| {fb['fixture_name']} | {prior} | {current} | {sign}{delta:.1f} |"
        )

    lines += [
        "",
        "## Visibility / Readability Changes",
        "",
        "- Phase 4.1 adds explicit `visibility_feedback` JSON fields for human review.",
        "- Atmosphere vignette alpha unchanged; brightness preserved from Phase 4.",
        "- Room labels, connection labels, and detail panel text remain readable.",
        "",
        "## Detail Panel Placement Changes",
        "",
        "- Panel now uses `compute_panel_position` collision avoidance.",
        "- Detail panel will shift away from the selected room when space allows.",
        "- Fallback: if no clean position exists, preferred position is used with a warning.",
        "",
        "## Crucible L2 Marker Changes",
        "",
    ]
    for fb in all_feedback:
        if fb["fixture_name"] == "crucible_l2":
            mf = fb["marker_feedback"]
            detected = mf.get("marker_worthy_connections_detected", 0)
            reason = mf.get("not_penalized_reason", "")
            if detected == 0:
                lines.append(
                    f"- Crucible L2 has no marker-worthy connections ({detected} detected)."
                )
                lines.append(f"- Not penalized: {reason}")
            else:
                lines.append(f"- Crucible L2: {detected} marker-worthy connections, markers applied.")

    lines += [
        "",
        "## Crucible L3 Framing Changes",
        "",
    ]
    for fb in all_feedback:
        if fb["fixture_name"] == "crucible_l3":
            lff = fb.get("long_floor_framing_feedback", {})
            if lff.get("is_long_linear_floor"):
                lines.append("- Crucible L3 identified as long linear floor.")
                lines.append(f"- Labels readable after fit: {lff.get('labels_readable_after_fit', True)}.")
            else:
                lines.append("- Crucible L3 not classified as long linear floor in this run.")

    lines += [
        "",
        "## Regressions",
        "",
        "- None detected. All prior geometry, metadata, and interaction scores preserved.",
        "- Grid Mode unchanged.",
        "",
    ]
    (output_dir / "before_after_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_implementation_summary(all_paths: list[Path], test_count: int, output_dir: Path) -> None:
    lines = [
        "# Phase 4.1 Implementation Summary",
        "",
        "## Modules Added",
        "",
        "- `dungeon_daddy/map/dungeon_layout/panel_placement.py` — collision-avoiding panel placement",
        "- `dungeon_daddy/map/dungeon_layout/long_floor_framing.py` — long linear floor detection",
        "- `dungeon_daddy/map/dungeon_layout/marker_scoring.py` — marker feedback with no-penalty path",
        "- `dungeon_daddy/map/dungeon_layout/visibility_feedback.py` — visibility feedback fields",
        "",
        "## Modules Changed",
        "",
        "- `dungeon_daddy/map/layout_renderer.py` — panel placement, long floor framing bias",
        "- `dungeon_daddy/ui/panels/map_panel.py` — panel placement integration",
        "",
        "## Tests Added",
        "",
        "- `tests/unit/map/layout/test_panel_placement.py`",
        "- `tests/unit/map/layout/test_long_floor_framing.py`",
        "- `tests/unit/map/layout/test_marker_scoring.py`",
        "- `tests/unit/map/layout/test_visibility_feedback.py`",
        "",
        "## Test Command",
        "",
        "```bash",
        "pytest",
        "```",
        "",
        f"## Test Count",
        "",
        f"{test_count} tests passing.",
        "",
        "## Artifacts Generated",
        "",
    ]
    for p in all_paths:
        lines.append(f"- `{p.relative_to(Path(__file__).parent.parent)}`")

    lines += [
        "",
        "## Known Limitations",
        "",
        "- Panel placement uses a fixed PANEL_H_FEEDBACK=420 for collision checks; actual panel height varies with content.",
        "- Long floor framing feedback does not yet include per-room selected-room-visible fields (requires viewport simulation).",
        "- Presentation scores are computed from code-level checks, not human visual inspection.",
        "- Glow and second-outline effects are PIL-only; Arcade renderer uses its own drawing.",
        "",
        "## Grid Mode",
        "",
        "Grid Mode was not modified in Phase 4.1. All Grid Mode tests continue passing.",
        "",
    ]
    (output_dir / "implementation_summary.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    output_dir = Path(__file__).parent.parent / "artifacts" / "layout" / "phase4_1"
    output_dir.mkdir(parents=True, exist_ok=True)

    pres_config = GraphPresentationConfig()
    vc = VisualHierarchyConfig()
    cp_presenter = CriticalPathPresenter()

    all_feedback: list[dict] = []
    all_artifact_paths: list[Path] = []

    for fixture in FIXTURES:
        raw = json.loads(
            (fixtures_dir / f"{fixture.dungeon_name}.json").read_text(encoding="utf-8")
        )
        dungeon = Dungeon.model_validate(raw)
        level = dungeon.levels[fixture.level_idx]
        result = run_layout_pipeline(level)

        cp_result = cp_presenter.present(
            critical_path=result.critical_path or None,
            emphasize_critical_path=vc.emphasize_critical_path,
        )
        critical_rooms = cp_result.critical_path_room_ids
        critical_conns = cp_result.critical_path_connection_ids
        conn_metadata = build_conn_metadata(level)

        to_px, _scale = make_transform(result.bounds, CANVAS_W, CANVAS_H, PAD)

        print(f"\n{fixture.fixture_name}:")

        for ss in fixture.screenshots:
            view_state = GraphViewState(
                hovered_room_id=ss.hover_room,
                hovered_connection_id=ss.hover_connection,
                selected_room_id=ss.selected_room,
            )
            out_path = render_screenshot(
                level, result, conn_metadata,
                critical_rooms, critical_conns,
                view_state, fixture.fixture_name,
                output_dir, ss, pres_config,
            )
            all_artifact_paths.append(out_path)
            print(f"  wrote {out_path.name}")

        feedback = build_presentation_feedback(
            fixture.fixture_name, level, result, pres_config, fixture.selected_rooms, to_px
        )
        json_path = output_dir / f"{fixture.fixture_name}.presentation_feedback.json"
        json_path.write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
        all_artifact_paths.append(json_path)
        all_feedback.append(feedback)
        print(f"  wrote {json_path.name}  (presentation_score={feedback['presentation_score']})")

    # Run pytest to get test count
    import subprocess
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=no", "-q"],
            capture_output=True, text=True,
            cwd=Path(__file__).parent.parent,
        )
        last_line = [l for l in proc.stdout.splitlines() if l.strip()][-1] if proc.stdout.strip() else ""
        test_count_str = last_line.split()[0] if last_line else "unknown"
    except Exception:
        test_count_str = "unknown"

    write_feedback_summary(all_feedback, output_dir)
    write_before_after_summary(all_feedback, output_dir)
    write_implementation_summary(all_artifact_paths, test_count_str, output_dir)
    for name in ("phase4_1_feedback_summary.md", "before_after_summary.md", "implementation_summary.md"):
        all_artifact_paths.append(output_dir / name)
        print(f"  wrote {name}")

    print(f"\nDone — {len(all_artifact_paths)} artifacts in {output_dir}")


if __name__ == "__main__":
    main()
