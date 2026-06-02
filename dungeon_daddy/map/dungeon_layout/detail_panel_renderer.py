from __future__ import annotations

import textwrap
from dataclasses import dataclass

from dungeon_daddy.map.dungeon_layout.room_detail_panel import RoomDetailPanelData

_MAX_NOTE_LEN = 200
_MAX_LINE_CHARS = 38


@dataclass
class PanelLine:
    text: str
    kind: str  # "header", "section", "value", "empty"


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
