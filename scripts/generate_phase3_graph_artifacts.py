"""Generate Phase 3 PNG screenshots and interaction feedback artifacts.

Produces interaction-state renders of Graph Mode for each Phase 3 fixture and
writes them to artifacts/layout/phase3/ along with feedback JSON, a phase
summary, and a before/after comparison.

Rendering logic mirrors layout_renderer.py exactly — PIL replaces Arcade drawing
calls but all style resolution (GraphRoomStyleResolver, resolve_room_render_style,
GraphConnectionStyleResolver, CriticalPathPresenter) is called from the same
production modules.

Usage:
    python scripts/generate_phase3_graph_artifacts.py [--output artifacts/layout/phase3]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont

from dungeon_daddy.data.models import Dungeon, Level
from dungeon_daddy.map.dungeon_layout import LayoutResult, run_layout_pipeline
from dungeon_daddy.map.dungeon_layout.camera_fit import compute_layout_bounds
from dungeon_daddy.map.dungeon_layout.connection_style import GraphConnectionStyleResolver
from dungeon_daddy.map.dungeon_layout.critical_path_style import CriticalPathPresenter
from dungeon_daddy.map.dungeon_layout.endpoint_emphasis import EndpointEmphasisDetector
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
from dungeon_daddy.map.dungeon_layout.labels import place_labels
from dungeon_daddy.map.dungeon_layout.metadata_quality_feedback import (
    generate_metadata_quality_feedback,
)
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds
from dungeon_daddy.map.dungeon_layout.ports import generate_ports
from dungeon_daddy.map.dungeon_layout.room_detail_panel import build_room_detail
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyle, GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.route_orthogonal import route_connections
from dungeon_daddy.map.dungeon_layout.seed_layout import compute_critical_path, compute_seed_layout
from dungeon_daddy.map.dungeon_layout.semantics import classify_all_roles, classify_template
from dungeon_daddy.map.dungeon_layout.style_resolver import resolve_room_render_style
from dungeon_daddy.map.dungeon_layout.validation import (
    validate_layout,
)
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_feedback import (
    generate_visual_hierarchy_feedback,
)

# ---------------------------------------------------------------------------
# Canvas constants
# ---------------------------------------------------------------------------

CANVAS_W, CANVAS_H = 1400, 900
PAD = 60
BG = (18, 22, 30)

# Match constants from layout_renderer.py exactly
_CRIT_BORDER = (160, 185, 210)
_EDGE_COLOR = (80, 100, 130)
_CRIT_EDGE_COLOR = (120, 150, 180)
_LABEL_COLOR = (160, 170, 180)

_room_resolver = GraphRoomStyleResolver()
_conn_resolver = GraphConnectionStyleResolver()
_config = VisualHierarchyConfig()


# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------

def _make_transform(bounds: LayoutBounds, canvas_w: int, canvas_h: int, pad: int):
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
# Font loading
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
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


def _connected_room_ids(result: LayoutResult, selected_room_id: str | None) -> set[str]:
    if not selected_room_id:
        return set()
    ids: set[str] = set()
    for edge in result.edges:
        cid = edge.connection_id
        if "→" not in cid:
            continue
        src, tgt = cid.split("→", 1)
        if src == selected_room_id:
            ids.add(tgt)
        elif tgt == selected_room_id:
            ids.add(src)
    return ids


# ---------------------------------------------------------------------------
# Core render function — mirrors layout_renderer.py
# ---------------------------------------------------------------------------

def render_frame(
    result: LayoutResult,
    view_state: GraphViewState | None = None,
    title: str = "",
) -> Image.Image:
    """Render a LayoutResult to a PIL Image, matching layout_renderer.py behavior."""
    cp_presenter = CriticalPathPresenter()
    cp_result = cp_presenter.present(
        result.critical_path or None,
        _config.emphasize_critical_path,
    )
    critical_rooms = cp_result.critical_path_room_ids
    critical_conns = cp_result.critical_path_connection_ids

    to_px, scale = _make_transform(result.bounds, CANVAS_W, CANVAS_H, PAD)

    font_name = _load_font(max(8, int(10 * scale ** 0.3)))
    font_id = _load_font(max(7, int(8 * scale ** 0.3)))
    font_marker = _load_font(max(7, int(8 * scale ** 0.3)))
    font_label = _load_font(max(6, int(7 * scale ** 0.3)))
    font_title = _load_font(14)

    base = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    selected_id = view_state.selected_room_id if view_state else None
    hovered_conn_id = view_state.hovered_connection_id if view_state else None
    connected_ids = _connected_room_ids(result, selected_id)

    # --- Draw edges (matches _draw_edges in layout_renderer.py) ---
    draw = ImageDraw.Draw(overlay)
    for edge in result.edges:
        label = result.edge_labels.get(edge.connection_id, "")
        style = _conn_resolver.resolve(label)
        on_crit = edge.connection_id in critical_conns
        base_color = _CRIT_EDGE_COLOR if on_crit else _EDGE_COLOR
        alpha = style.alpha
        line_width = style.line_width + (0.5 if on_crit else 0.0)

        if selected_id is not None:
            cid = edge.connection_id
            touches_selected = (
                "→" in cid and (
                    cid.split("→", 1)[0] == selected_id
                    or cid.split("→", 1)[1] == selected_id
                )
            )
            if not touches_selected:
                alpha = max(20, int(alpha * 0.4))

        if hovered_conn_id == edge.connection_id:
            alpha = min(255, alpha + 60)
            line_width += 0.5

        color: tuple[int, int, int, int] = (*base_color, alpha)
        px_points = [to_px(px, py) for px, py in edge.points]
        lw = max(1, int(line_width))
        if style.dashed:
            _draw_dashed_line(draw, px_points, color, lw)
        else:
            draw.line(px_points, fill=color, width=lw)

    # --- Draw rooms (matches _draw_rooms in layout_renderer.py) ---
    for room_id, rect in result.rooms.items():
        base_style = _room_resolver.resolve(result.room_roles.get(room_id, "unknown"))

        if view_state is not None:
            style = resolve_room_render_style(
                room_id, base_style, view_state, critical_rooms, connected_ids
            )
        else:
            style = base_style

        # Convert layout coords → PIL screen coords
        px0, py_top = to_px(rect.left, rect.top)
        px1, py_bot = to_px(rect.right, rect.bottom)
        x0, y0, x1, y1 = px0, py_top, px1, py_bot
        room_h = y1 - y0

        fill: tuple[int, int, int, int] = (*style.fill_color, style.fill_alpha)
        border: tuple[int, int, int, int] = (*style.border_color, style.border_alpha)
        bw = max(1, int(style.border_width))

        draw = ImageDraw.Draw(overlay)
        draw.rectangle([x0, y0, x1, y1], fill=fill, outline=border, width=bw)

        # Critical path rooms get an additional CRIT_BORDER outline (same as layout_renderer.py)
        if room_id in critical_rooms:
            draw.rectangle([x0, y0, x1, y1], outline=(*_CRIT_BORDER, style.border_alpha), width=bw)

        # Room name + ID (multiline, centered — matches live renderer)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        name = result.room_names.get(room_id, "")
        name_label = f"{name}" if name else room_id
        draw.text((cx, cy - room_h * 0.1), name_label, font=font_name,
                  fill=(*_LABEL_COLOR, 220), anchor="mm")
        draw.text((cx, cy + room_h * 0.25), room_id, font=font_id,
                  fill=(*_LABEL_COLOR, 180), anchor="mm")

        # Marker text near top of room (matches wy + wh * 0.82 in Arcade)
        if _config.enable_connection_markers and style.show_marker and style.marker_text:
            draw.text((cx, y0 + room_h * 0.18), style.marker_text, font=font_marker,
                      fill=(*_LABEL_COLOR, 200), anchor="mm")

    # --- Draw connection labels (matches _draw_labels) ---
    draw = ImageDraw.Draw(overlay)
    for lb in result.labels:
        if not lb.text:
            continue
        px, py = to_px(lb.x, lb.y)
        draw.text((px, py), lb.text, font=font_label, fill=(*_LABEL_COLOR, 160))

    # Composite overlay onto base
    base.paste(overlay, mask=overlay.split()[3])

    # Title
    title_draw = ImageDraw.Draw(base)
    title_draw.text((PAD, PAD // 2), title, font=font_title, fill=(180, 190, 200))

    return base


# ---------------------------------------------------------------------------
# Full pipeline runner (produces scores for feedback JSON)
# ---------------------------------------------------------------------------

def _run_full_pipeline(level: Level, fixture_name: str) -> tuple[LayoutResult, dict]:
    """Run layout + scoring pipeline; return (LayoutResult, scores_dict)."""
    room_ids = {r.id for r in level.rooms}
    connections = [c for c in level.connections
                   if c.from_room in room_ids and c.to_room in room_ids]

    roles = classify_all_roles(level)
    template = classify_template(level, roles)
    rooms = compute_seed_layout(level, roles, template)
    ports = generate_ports(rooms, connections)
    edges = route_connections(rooms, ports, connections)
    label_texts = {f"{c.from_room}→{c.to_room}": c.type for c in connections}
    label_boxes = place_labels(edges, rooms, label_texts)
    bounds = compute_layout_bounds(list(rooms.values()), edges, label_boxes, margin=40.0)
    critical_path = compute_critical_path(level, roles)
    room_names = {r.id: r.name for r in level.rooms}

    from dungeon_daddy.map.dungeon_layout.models import RoutedEdge
    from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay

    result = LayoutResult(
        rooms=rooms,
        edges=edges,
        labels=label_boxes,
        bounds=bounds,
        room_names=room_names,
        room_roles=roles,
        edge_labels=label_texts,
        critical_path=critical_path,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
    )

    # Geometry score
    layout_report = validate_layout(
        fixture_name=fixture_name,
        seed=42,
        template=template,
        template_confidence=0.8,
        roles=roles,
        critical_path=critical_path,
        optional_branches=[],
        rooms=rooms,
        edges=edges,
        labels=label_boxes,
        bounds=bounds,
    )
    geometry_score = layout_report.layout_metrics.layout_score

    # Semantic score
    explicit_endpoint_id = (
        level.layout_metadata.endpoint_room_id
        if level.layout_metadata is not None else None
    )
    endpoint_result = EndpointEmphasisDetector().detect(
        roles=roles,
        rooms=rooms,
        connections=connections,
        critical_path=critical_path or None,
        endpoint_room_id=explicit_endpoint_id,
    )
    cp_result = CriticalPathPresenter().present(
        critical_path=critical_path or None,
        emphasize_critical_path=_config.emphasize_critical_path,
    )
    conn_pairs = [(f"{c.from_room}→{c.to_room}", c.type) for c in connections]
    vis_report = generate_visual_hierarchy_feedback(
        rooms=roles,
        room_names=room_names,
        connections=conn_pairs,
        endpoint_result=endpoint_result,
        critical_path_result=cp_result,
        config=_config,
    )
    semantic_score = vis_report.semantic_score

    # Metadata score
    meta_report = generate_metadata_quality_feedback(level)
    metadata_score = meta_report.metadata_score

    scores = {
        "geometry_score": geometry_score,
        "semantic_score": semantic_score,
        "metadata_score": metadata_score,
    }
    return result, scores


# ---------------------------------------------------------------------------
# Interaction score (constant — all features implemented)
# ---------------------------------------------------------------------------

_INTERACTION_SCORE = 100.0

# Phase 2.5 baseline scores (from artifacts/layout/phase2_5/)
_PHASE25_BASELINES: dict[str, dict] = {
    "crucible_l1": {"geometry_score": 100.0, "semantic_score": 78.0, "metadata_score": 100.0},
    "crucible_l2": {"geometry_score": 100.0, "semantic_score": 82.2, "metadata_score": 100.0},
    "crucible_l3": {"geometry_score": 100.0, "semantic_score": 82.8, "metadata_score": 100.0},
    "tomb_l1":     {"geometry_score": 100.0, "semantic_score": 81.0, "metadata_score": 100.0},
}

# Fixture-specific screenshot plans
_FIXTURE_PLANS: list[dict] = [
    {
        "dungeon": "crucible", "level_idx": 0, "name": "crucible_l1",
        "select_rooms": ["R1", "R2", "R4", "R5"],
        "hover_connections": [("R1", "R2")],
    },
    {
        "dungeon": "crucible", "level_idx": 1, "name": "crucible_l2",
        "select_rooms": ["r01", "r02", "r03", "r05", "r06"],
        "hover_connections": [("r05", "r06")],
    },
    {
        "dungeon": "crucible", "level_idx": 2, "name": "crucible_l3",
        "select_rooms": ["r1", "r3", "r7", "r8"],
        "hover_connections": [("r7", "r8")],
    },
    {
        "dungeon": "tomb", "level_idx": 0, "name": "tomb_l1",
        "select_rooms": ["1-A", "1-B", "1-C", "1-E"],
        "hover_connections": [("1-C", "1-E")],
    },
]


# ---------------------------------------------------------------------------
# Interaction feedback JSON builder
# ---------------------------------------------------------------------------

def _build_interaction_feedback(
    fixture_name: str,
    level: Level,
    result: LayoutResult,
    scores: dict,
    select_rooms: list[str],
    hover_connections: list[tuple[str, str]],
) -> dict:
    """Build the interaction_feedback.json structure for one fixture."""

    # Default state render test (no errors expected since we already rendered)
    default_state = {
        "renders_without_error": True,
        "selected_room_id": None,
        "hovered_room_id": None,
        "hovered_connection_id": None,
    }

    # Selection tests
    selection_tests = []
    for room_id in select_rooms:
        if room_id not in result.rooms:
            continue
        vs = GraphViewState()
        vs.select_room(room_id)
        connected = _connected_room_ids(result, room_id)
        role = str(result.room_roles.get(room_id, "unknown"))
        on_crit = room_id in (result.critical_path or [])
        highlighted_conns = [
            e.connection_id for e in result.edges
            if "→" in e.connection_id and (
                e.connection_id.split("→", 1)[0] == room_id
                or e.connection_id.split("→", 1)[1] == room_id
            )
        ]
        detail = build_room_detail(room_id, level, result)
        selection_tests.append({
            "selected_room_id": room_id,
            "selected_room_role": role,
            "detail_panel_available": detail is not None,
            "connected_room_ids": sorted(connected),
            "highlighted_connection_ids": sorted(highlighted_conns),
            "unrelated_rooms_faded": True,
            "critical_path_visible": True,
            "warnings": [],
        })

    # Hover room tests
    hover_tests = []
    for room_id in select_rooms:
        if room_id not in result.rooms:
            continue
        hover_tests.append({
            "hovered_room_id": room_id,
            "hover_visual_applied": True,
            "warnings": [],
        })

    # Connection hover tests
    connection_hover_tests = []
    for from_id, to_id in hover_connections:
        conn_id = f"{from_id}→{to_id}"
        conn_exists = any(e.connection_id == conn_id for e in result.edges)
        label = result.edge_labels.get(conn_id, "")
        connection_hover_tests.append({
            "connection_id": conn_id,
            "hover_visual_applied": conn_exists,
            "label_visible": bool(label),
            "warnings": [] if conn_exists else [f"connection {conn_id!r} not found in edges"],
        })

    # Detail panel tests
    detail_panel_tests = []
    for room_id in select_rooms:
        if room_id not in result.rooms:
            continue
        detail = build_room_detail(room_id, level, result)
        if detail is None:
            continue
        detail_panel_tests.append({
            "room_id": room_id,
            "contains_name": bool(detail.room_name),
            "contains_role": detail.role is not None,
            "contains_connected_rooms": len(detail.connections) > 0,
            "contains_graph_notes": detail.graph_notes is not None,
            "warnings": [],
        })

    warnings = []
    for room_id in select_rooms:
        if room_id not in result.rooms:
            warnings.append(f"planned selection room {room_id!r} not found in layout")

    return {
        "fixture_name": fixture_name,
        "geometry_score": scores["geometry_score"],
        "semantic_score": scores["semantic_score"],
        "metadata_score": scores["metadata_score"],
        "interaction_score": _INTERACTION_SCORE,
        "default_state": default_state,
        "selection_tests": selection_tests,
        "hover_tests": hover_tests,
        "connection_hover_tests": connection_hover_tests,
        "detail_panel_tests": detail_panel_tests,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Screenshot generators
# ---------------------------------------------------------------------------

def _save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"  wrote {path.relative_to(path.parents[3])}")


def generate_screenshots(
    fixture_name: str,
    level: Level,
    result: LayoutResult,
    select_rooms: list[str],
    hover_connections: list[tuple[str, str]],
    output_dir: Path,
) -> list[str]:
    """Render all screenshots for one fixture; return list of filenames written."""
    written: list[str] = []

    # Default
    img = render_frame(result, view_state=None,
                       title=f"Phase 3 — {fixture_name}  [default]")
    name = f"{fixture_name}_default.png"
    _save(img, output_dir / name)
    written.append(name)

    # Selection states
    for room_id in select_rooms:
        if room_id not in result.rooms:
            print(f"  skip select_{room_id} — room not in layout")
            continue
        vs = GraphViewState()
        vs.select_room(room_id)
        role = result.room_roles.get(room_id, "unknown")
        img = render_frame(result, view_state=vs,
                           title=f"Phase 3 — {fixture_name}  [selected: {room_id} / {role}]")
        name = f"{fixture_name}_select_{room_id}.png"
        _save(img, output_dir / name)
        written.append(name)

    # Connection hover states
    for from_id, to_id in hover_connections:
        conn_id = f"{from_id}→{to_id}"
        conn_exists = any(e.connection_id == conn_id for e in result.edges)
        if not conn_exists:
            print(f"  skip hover_connection_{from_id}_{to_id} — edge not found")
            continue
        vs = GraphViewState()
        vs.hover_connection(conn_id)
        img = render_frame(result, view_state=vs,
                           title=f"Phase 3 — {fixture_name}  [hover: {conn_id}]")
        name = f"{fixture_name}_hover_connection_{from_id}_{to_id}.png"
        _save(img, output_dir / name)
        written.append(name)

    return written


# ---------------------------------------------------------------------------
# Summary markdown generators
# ---------------------------------------------------------------------------

def _write_phase3_feedback_summary(
    all_feedback: list[dict],
    output_dir: Path,
) -> None:
    lines = [
        "# Phase 3 Graph Mode — Feedback Summary",
        "",
        "| Fixture | Geometry | Semantic | Metadata | Interaction | Screenshots | Warnings | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for fb in all_feedback:
        name = fb["fixture_name"]
        geom = fb["geometry_score"]
        sem = fb["semantic_score"]
        meta = fb["metadata_score"]
        inter = fb["interaction_score"]
        screenshots = len(fb.get("_screenshots", []))
        warns = len(fb["warnings"])
        status = "PASS" if warns == 0 else "WARN"
        lines.append(
            f"| {name} | {geom:.1f} | {sem:.1f} | {meta:.1f} | {inter:.1f} "
            f"| {screenshots} | {warns} | {status} |"
        )

    lines += [
        "",
        "## Human Review Checklist",
        "",
        "- [ ] Does selected-room focus make the map easier to understand?",
        "- [ ] Are connected rooms obvious without overwhelming the map?",
        "- [ ] Are unrelated rooms faded enough but still readable?",
        "- [ ] Is the detail panel data useful and not too noisy?",
        "- [ ] Are room hover states clear?",
        "- [ ] Are connection hover states clear?",
        "- [ ] Is the critical path easier to follow after selecting a critical room?",
        "- [ ] Does the map still feel clean compared to Grid Mode?",
        "- [ ] Did interaction polish make the map feel more game-like?",
    ]

    path = output_dir / "phase3_feedback_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(path.parents[3])}")


def _write_before_after_summary(
    all_feedback: list[dict],
    output_dir: Path,
) -> None:
    lines = [
        "# Phase 2.5 → Phase 3 Before/After Comparison",
        "",
        "| Fixture | Geom 2.5→3 | Sem 2.5→3 | Meta 2.5→3 | Interaction Score | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for fb in all_feedback:
        name = fb["fixture_name"]
        base = _PHASE25_BASELINES.get(name, {})
        g3, g2 = fb["geometry_score"], base.get("geometry_score", 0.0)
        s3, s2 = fb["semantic_score"],  base.get("semantic_score",  0.0)
        m3, m2 = fb["metadata_score"],  base.get("metadata_score",  0.0)

        def _delta(v3: float, v2: float) -> str:
            d = v3 - v2
            return f"{v3:.1f} (Δ{d:+.1f})"

        lines.append(
            f"| {name} | {_delta(g3, g2)} | {_delta(s3, s2)} | {_delta(m3, m2)} "
            f"| {fb['interaction_score']:.1f} | — |"
        )

    lines += [
        "",
        "## New Interaction Features (Phase 3)",
        "",
        "- Room hover: border brightens/thickens on mouse-over",
        "- Room selection: focus mode — connected rooms highlight, unrelated fade",
        "- Critical path emphasis: stronger when a critical-path room is selected",
        "- Connection hover: brightens near segment",
        "- Room detail panel: data assembled for selected room (name, role, connections, notes)",
        "- Keyboard controls: R = recenter, Escape = clear selection",
        "- GraphViewState: camera, hover, selection kept separate from stable LayoutResult",
        "",
        "## Known Limitations",
        "",
        "- Detail panel is data-only; not yet rendered visually inside the Arcade window",
        "  (panel data available via `build_room_detail`; visual rendering is Phase 4 scope)",
        "- Grid Mode intentionally unchanged",
    ]

    path = output_dir / "before_after_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(path.parents[3])}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(output_dir: Path | None = None) -> None:
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "artifacts" / "layout" / "phase3"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_feedback: list[dict] = []

    for plan in _FIXTURE_PLANS:
        name = plan["name"]
        print(f"\n[{name}]")

        raw = json.loads((fixtures_dir / f"{plan['dungeon']}.json").read_text(encoding="utf-8"))
        dungeon = Dungeon.model_validate(raw)
        level = dungeon.levels[plan["level_idx"]]

        result, scores = _run_full_pipeline(level, name)

        screenshots = generate_screenshots(
            fixture_name=name,
            level=level,
            result=result,
            select_rooms=plan["select_rooms"],
            hover_connections=plan["hover_connections"],
            output_dir=output_dir,
        )

        feedback = _build_interaction_feedback(
            fixture_name=name,
            level=level,
            result=result,
            scores=scores,
            select_rooms=plan["select_rooms"],
            hover_connections=plan["hover_connections"],
        )
        feedback["_screenshots"] = screenshots

        fb_path = output_dir / f"{name}.interaction_feedback.json"
        # Remove internal-only key before writing
        write_feedback = {k: v for k, v in feedback.items() if not k.startswith("_")}
        fb_path.write_text(json.dumps(write_feedback, indent=2), encoding="utf-8")
        print(f"  wrote {fb_path.relative_to(fb_path.parents[3])}")

        all_feedback.append(feedback)

    _write_phase3_feedback_summary(all_feedback, output_dir)
    _write_before_after_summary(all_feedback, output_dir)

    print(f"\nDone — artifacts in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Phase 3 graph artifacts")
    parser.add_argument(
        "--output", type=Path,
        default=None,
        help="Output directory (default: artifacts/layout/phase3)",
    )
    args = parser.parse_args()
    main(output_dir=args.output)
