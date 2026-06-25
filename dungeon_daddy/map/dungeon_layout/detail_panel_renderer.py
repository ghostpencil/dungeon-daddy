from __future__ import annotations

import textwrap
from dataclasses import dataclass

from dungeon_daddy.map.dungeon_layout.room_detail_panel import RoomDetailPanelData
from dungeon_daddy.rpg.action_options import RoomThings

_MAX_NOTE_LEN = 200
_MAX_LINE_CHARS = 38

# Per-row selection markers for the "Things Here" overlay (Slice 8). The marker
# is part of the row text so it stays aligned with the label; the pointer ▸ marks
# the selected noun, a quiet · marks the rest. Both live in already-rendered
# Unicode blocks (Geometric Shapes / Latin-1), so no PNG assets are needed.
_SEL_MARKER = "▸"
_UNSEL_MARKER = "·"


@dataclass
class PanelLine:
    text: str
    kind: str  # "header", "section", "value", "empty", "thing", "footer"
    # "thing" rows (Things Here overlay) carry a trailing status chip:
    status: str | None = None
    status_color: str | None = None  # "teal" | "ember" | "gold" | "default"
    # "thing" rows also carry the noun id they feed into the builder, a selection
    # flag, and a leading marker glyph the renderer draws (larger for the selected
    # row) as the per-row selected/deselected icon (Slice 8).
    noun_id: str | None = None
    selected: bool = False
    marker: str | None = None


def format_detail_panel(
    data: RoomDetailPanelData | None,
    max_note_len: int = _MAX_NOTE_LEN,
    max_line_chars: int = _MAX_LINE_CHARS,
) -> list[PanelLine]:
    if data is None:
        return [
            PanelLine("GRAPH MODE", "header"),
            PanelLine("Select a room to inspect it.", "value"),
            PanelLine("Hover connections to inspect paths.", "value"),
            PanelLine("R recenter · Esc clear", "value"),
        ]

    lines: list[PanelLine] = []

    lines.append(PanelLine("ROOM", "header"))
    lines.append(PanelLine(data.room_name, "value"))
    lines.append(PanelLine(f"{data.room_id} · {data.role or '—'}", "value"))

    lines.append(PanelLine("Status", "section"))
    lines.append(PanelLine(f"Critical Path: {'Yes' if data.on_critical_path else 'No'}", "value"))
    if data.visual_priority:
        lines.append(PanelLine(f"Visual Priority: {data.visual_priority.title()}", "value"))
    if data.on_optional_branch:
        lines.append(PanelLine("Optional Branch: Yes", "value"))

    if data.connections:
        lines.append(PanelLine("Connections", "section"))
        for conn in data.connections:
            parts = [conn.label]
            if conn.role:
                parts.append(conn.role.replace("_", " "))
            label_str = " · ".join(parts)
            full_text = f"→ {conn.room_name} · {label_str}"
            for segment in textwrap.wrap(full_text, width=max_line_chars, subsequent_indent="  ") or [full_text]:
                lines.append(PanelLine(segment, "value"))

    notes = data.graph_notes or data.note
    if notes:
        lines.append(PanelLine("Notes", "section"))
        if len(notes) > max_note_len:
            notes = notes[:max_note_len].rstrip() + "…"
        for wrapped in textwrap.wrap(notes, width=max_line_chars) or [notes]:
            lines.append(PanelLine(wrapped, "value"))

    return lines


def format_things_here(
    things: RoomThings,
    selected_noun_id: str | None = None,
    suggested_verbs: list[str] | None = None,
) -> list[PanelLine]:
    """Render the play-mode "Things Here" overlay content (Phase 50.6 §5.1, §5.3).

    Pure: turns the :class:`RoomThings` view-model into drawable panel lines —
    a header, the room id, then each section title followed by its clickable
    rows. Each ``"thing"`` row carries its ``status``/``status_color`` (for the
    trailing status chip) plus its ``noun_id`` and a ``selected`` flag — the row
    matching ``selected_noun_id`` is flagged so the renderer can draw a TEAL
    selection ring (Slice 8). When a noun is selected, a footer mirrors the
    suggested verbs for it (``suggested_verbs``) and states the contract that
    clicking a noun feeds the action builder. Replaces the technical
    graph-metadata readout (``format_detail_panel``) when the map is in play mode.
    """
    lines: list[PanelLine] = [PanelLine("THINGS HERE", "header")]
    if things.room_id:
        lines.append(PanelLine(things.room_id, "value"))

    if not things.sections:
        lines.append(PanelLine("Nothing of note here.", "value"))
        return lines

    selected_label: str | None = None
    for section in things.sections:
        lines.append(PanelLine(section.title, "section"))
        for thing in section.things:
            is_selected = thing.noun_id == selected_noun_id
            if is_selected:
                selected_label = thing.label
            lines.append(PanelLine(
                f"{thing.glyph} {thing.label}",
                "thing",
                status=thing.status,
                status_color=thing.status_color,
                noun_id=thing.noun_id,
                selected=is_selected,
                marker=_SEL_MARKER if is_selected else _UNSEL_MARKER,
            ))

    if selected_label is not None:
        lines.append(PanelLine(f"Selected: {selected_label}", "footer"))
        if suggested_verbs:
            lines.append(PanelLine("Suggested: " + ", ".join(suggested_verbs), "footer"))
        lines.append(PanelLine("Clicking a noun feeds the action builder.", "footer"))
    return lines
