"""Generate PNG screenshots of dungeon layout fixtures using Pillow.

Produces graph-mode layout renders for each Phase 2 test fixture and writes
them to artifacts/layout/phase2/.

Usage:
    python tools/generate_layout_screenshots.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root without pip install
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont

from dungeon_daddy.data.models import Dungeon, Level
from dungeon_daddy.map.dungeon_layout import run_layout_pipeline
from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyleResolver
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresenter
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoutedEdge
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANVAS_W, CANVAS_H = 1400, 900
PAD = 60
BG = (18, 22, 30)
ROOM_BASE_FILL = (30, 35, 45)
BORDER_BASE = (100, 120, 140)
EDGE_BASE = (80, 100, 130)
CRIT_EDGE = (140, 165, 200)
LABEL_COLOR = (150, 160, 170)
MARKER_COLOR = (200, 210, 225)
TEXT_COLOR = (190, 200, 215)

# Role-tinted border hues (R, G, B base)
_ROLE_TINTS: dict[str, tuple[int, int, int]] = {
    "entrance":  (100, 190, 160),
    "hub":       (120, 160, 220),
    "boss":      (200, 100, 100),
    "objective": (180, 130, 80),
    "exit":      (140, 200, 180),
    "descent":   (120, 180, 200),
    "elevator":  (120, 180, 200),
    "stairs":    (130, 190, 195),
    "key_room":  (200, 190, 100),
    "lock_room": (180, 140, 220),
    "treasure":  (210, 185, 90),
    "hazard":    (220, 120, 60),
    "secret":    (100, 100, 130),
}

_room_resolver = GraphRoomStyleResolver()
_conn_resolver = GraphConnectionStyleResolver()

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
        py = off_y + rendered_h - (ly - bounds.min_y) * scale  # flip y, centered
        return px, py

    return to_px, scale


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _tinted_border(role: str, alpha: int) -> tuple[int, int, int, int]:
    base = _ROLE_TINTS.get(role, BORDER_BASE)
    return (*base, alpha)


def _room_fill(role: str, fill_alpha: int) -> tuple[int, int, int, int]:
    base = _ROLE_TINTS.get(role, ROOM_BASE_FILL)
    r = int(ROOM_BASE_FILL[0] + (base[0] - ROOM_BASE_FILL[0]) * 0.4)
    g = int(ROOM_BASE_FILL[1] + (base[1] - ROOM_BASE_FILL[1]) * 0.4)
    b = int(ROOM_BASE_FILL[2] + (base[2] - ROOM_BASE_FILL[2]) * 0.4)
    return (r, g, b, fill_alpha)


def _edge_color(dashed: bool, alpha: int) -> tuple[int, int, int, int]:
    if dashed:
        return (80, 100, 130, max(60, alpha - 40))
    return (*EDGE_BASE, alpha)


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    color: tuple[int, int, int, int],
    width: int,
) -> None:
    dash_len, gap_len = 8, 5
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


def _draw_edge(
    overlay: Image.Image,
    edge: RoutedEdge,
    result_edge_labels: dict[str, str],
    to_px,
    is_critical: bool,
) -> None:
    label_str = result_edge_labels.get(edge.connection_id, "")
    style = _conn_resolver.resolve(label_str)

    draw = ImageDraw.Draw(overlay)
    px_points = [to_px(px, py) for px, py in edge.points]

    if is_critical:
        color = (*CRIT_EDGE, min(255, style.alpha + 30))
    else:
        color = _edge_color(style.dashed, style.alpha)

    line_w = max(1, int(style.line_width * (1.5 if is_critical else 1.0)))

    if style.dashed:
        _draw_dashed_line(draw, px_points, color, line_w)
    else:
        draw.line(px_points, fill=color, width=line_w)


def _draw_room(
    overlay: Image.Image,
    room_id: str,
    room_style,
    x0: float, y0: float, x1: float, y1: float,
    name: str,
    is_critical: bool,
    font_name: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_id: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_marker: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    role = room_style.key
    fill = _room_fill(role, room_style.fill_alpha)
    border = _tinted_border(role, room_style.border_alpha)
    bw = max(1, int(room_style.border_width * (1.5 if is_critical else 1.0)))

    draw = ImageDraw.Draw(overlay)
    draw.rectangle([x0, y0, x1, y1], fill=fill, outline=border, width=bw)

    if is_critical and bw >= 2:
        # Extra inner glow line
        draw.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=(*CRIT_EDGE, 80), width=1)

    # Room name (top half)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    room_h = y1 - y0
    draw.text((cx, cy - room_h * 0.1), name, font=font_name, fill=(*TEXT_COLOR, 220), anchor="mm")
    draw.text((cx, cy + room_h * 0.25), room_id, font=font_id, fill=(*LABEL_COLOR, 180), anchor="mm")

    # Marker
    if room_style.show_marker and room_style.marker_text:
        draw.text((cx, y0 + 5), room_style.marker_text, font=font_marker,
                  fill=(*MARKER_COLOR, 200), anchor="mt")


def _draw_conn_label(
    overlay: Image.Image,
    label: str,
    midpoint: tuple[float, float],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(overlay)
    draw.text(midpoint, label, font=font, fill=(*LABEL_COLOR, 160), anchor="mm")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_fixture(level: Level, fixture_name: str, output_dir: Path) -> Path:
    result = run_layout_pipeline(level)
    config = VisualHierarchyConfig()
    cp_presenter = CriticalPathPresenter()
    cp_result = cp_presenter.present(
        critical_path=result.critical_path or None,
        emphasize_critical_path=config.emphasize_critical_path,
    )
    critical_rooms = cp_result.critical_path_room_ids
    critical_conns = cp_result.critical_path_connection_ids

    to_px, scale = make_transform(result.bounds, CANVAS_W, CANVAS_H, PAD)

    font_name = _load_font(max(8, int(10 * scale ** 0.3)))
    font_id = _load_font(max(7, int(8 * scale ** 0.3)))
    font_marker = _load_font(max(7, int(8 * scale ** 0.3)))
    font_label = _load_font(max(6, int(7 * scale ** 0.3)))

    # Compose: background + RGBA overlay
    base = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    # Draw edges first
    for edge in result.edges:
        is_crit = edge.connection_id in critical_conns
        _draw_edge(overlay, edge, result.edge_labels, to_px, is_crit)

    # Draw rooms
    for room_id, rect in result.rooms.items():
        role = result.room_roles.get(room_id, "unknown")
        room_style = _room_resolver.resolve(role)
        px0, py1 = to_px(rect.left, rect.top)    # image top-left
        px1, py0 = to_px(rect.right, rect.bottom)  # image bottom-right
        is_crit = room_id in critical_rooms
        name = result.room_names.get(room_id, room_id)
        _draw_room(
            overlay, room_id, room_style,
            px0, py1, px1, py0,
            name, is_crit, font_name, font_id, font_marker,
        )

    # Draw connection labels
    for edge in result.edges:
        label = result.edge_labels.get(edge.connection_id, "")
        if label and len(edge.points) >= 2:
            mid_idx = len(edge.points) // 2
            mid = to_px(*edge.points[mid_idx])
            _draw_conn_label(overlay, label, mid, font_label)

    # Merge layers
    base.paste(overlay, mask=overlay.split()[3])

    # Fixture title
    title_draw = ImageDraw.Draw(base)
    title_font = _load_font(14)
    title_draw.text((PAD, PAD // 2), f"Phase 2 — {fixture_name}  [graph mode]",
                    font=title_font, fill=(180, 190, 200))

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{fixture_name}_graph.png"
    base.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    output_dir = Path(__file__).parent.parent / "artifacts" / "layout" / "phase2"

    fixture_specs = [
        ("crucible", 0, "crucible_l1"),
        ("crucible", 1, "crucible_l2"),
        ("crucible", 2, "crucible_l3"),
        ("tomb",     0, "tomb_l1"),
    ]

    for dungeon_name, level_idx, fixture_name in fixture_specs:
        raw = json.loads((fixtures_dir / f"{dungeon_name}.json").read_text(encoding="utf-8"))
        dungeon = Dungeon.model_validate(raw)
        level = dungeon.levels[level_idx]
        out_path = render_fixture(level, fixture_name, output_dir)
        print(f"  wrote {out_path}")

    print(f"\nDone — screenshots in {output_dir}")


if __name__ == "__main__":
    main()
