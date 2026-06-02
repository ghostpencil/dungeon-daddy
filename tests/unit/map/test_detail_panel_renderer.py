from dungeon_daddy.map.dungeon_layout.detail_panel_renderer import format_detail_panel, PanelLine
from dungeon_daddy.map.dungeon_layout.room_detail_panel import RoomDetailPanelData, ConnectionDetail


def _make_data(**kwargs) -> RoomDetailPanelData:
    defaults = dict(
        room_id="R1",
        room_name="Receiving Hall",
        role="entrance",
        visual_priority="high",
        on_critical_path=True,
        on_optional_branch=False,
        graph_notes="Starting chamber.",
        note="",
        connections=[],
    )
    defaults.update(kwargs)
    return RoomDetailPanelData(**defaults)


def test_empty_state_when_no_room():
    lines = format_detail_panel(None)
    assert len(lines) > 0
    all_text = " ".join(l.text for l in lines).lower()
    assert "select" in all_text or "graph mode" in all_text.lower()


def test_panel_includes_name_and_id():
    lines = format_detail_panel(_make_data())
    all_text = " ".join(l.text for l in lines)
    assert "Receiving Hall" in all_text
    assert "R1" in all_text


def test_panel_includes_role_and_critical_path():
    lines = format_detail_panel(_make_data(on_critical_path=True, role="entrance"))
    all_text = " ".join(l.text for l in lines)
    assert "entrance" in all_text
    assert "Yes" in all_text


def test_panel_includes_connections():
    conns = [ConnectionDetail("R2", "Marketplace", "arch", "critical_path", None)]
    lines = format_detail_panel(_make_data(connections=conns))
    all_text = " ".join(l.text for l in lines)
    assert "Marketplace" in all_text
    assert "arch" in all_text


def test_connection_format_uses_dots_not_brackets():
    conns = [ConnectionDetail("R2", "Marketplace", "arch", "critical_path", None)]
    lines = format_detail_panel(_make_data(connections=conns))
    conn_line = next(l for l in lines if "Marketplace" in l.text)
    assert "[" not in conn_line.text
    assert "·" in conn_line.text
    assert "critical path" in conn_line.text


def test_connection_role_underscores_replaced_with_spaces():
    conns = [ConnectionDetail("R2", "Vault", "door", "optional_branch", None)]
    lines = format_detail_panel(_make_data(connections=conns))
    conn_line = next(l for l in lines if "Vault" in l.text)
    assert "_" not in conn_line.text
    assert "optional branch" in conn_line.text


def test_connection_without_role_no_trailing_separator():
    conns = [ConnectionDetail("R2", "Side Room", "hall", None, None)]
    lines = format_detail_panel(_make_data(connections=conns))
    conn_line = next(l for l in lines if "Side Room" in l.text)
    assert conn_line.text.endswith("hall")


def test_long_connection_wraps_into_multiple_lines():
    conns = [ConnectionDetail("R2", "Maintenance Tunnel", "hole", "critical_path", None)]
    lines = format_detail_panel(_make_data(connections=conns), max_line_chars=30)
    conn_section = False
    conn_lines = []
    for line in lines:
        if line.kind == "section" and line.text == "Connections":
            conn_section = True
            continue
        if conn_section and line.kind == "section":
            break
        if conn_section and line.kind == "value":
            conn_lines.append(line)
    assert len(conn_lines) >= 2
    assert conn_lines[0].text.startswith("→")


def test_panel_includes_notes():
    lines = format_detail_panel(_make_data(graph_notes="Starting chamber."))
    all_text = " ".join(l.text for l in lines)
    assert "Starting chamber." in all_text


def test_long_notes_wrap_into_multiple_lines():
    # 80-char note with max_line_chars=30 should produce at least 2 note lines
    long_note = "word " * 16  # 80 chars
    lines = format_detail_panel(_make_data(graph_notes=long_note), max_line_chars=30)
    note_lines = [l for l in lines if l.kind == "value" and "word" in l.text]
    assert len(note_lines) >= 2


def test_long_notes_are_truncated():
    long_note = "x" * 500
    lines = format_detail_panel(_make_data(graph_notes=long_note), max_note_len=200)
    note_lines = [l for l in lines if "x" in l.text or "…" in l.text]
    assert len(note_lines) >= 1
    combined = "".join(l.text for l in note_lines)
    assert len(combined) <= 210  # 200 chars + ellipsis + wrapping overhead


def test_no_raw_json_in_lines():
    import json
    lines = format_detail_panel(_make_data())
    for line in lines:
        try:
            json.loads(line.text)
            assert False, f"Line looks like raw JSON: {line.text!r}"
        except (json.JSONDecodeError, ValueError):
            pass
