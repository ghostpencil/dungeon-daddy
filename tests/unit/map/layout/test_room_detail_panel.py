"""Unit tests for room_detail_panel.py — detail panel data assembly."""
from __future__ import annotations

from dungeon_daddy.data.models import Connection, LayoutMetadata, Level, Room
from dungeon_daddy.map.dungeon_layout import LayoutResult
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.models import LayoutBounds, RoomRect, RoutedEdge
from dungeon_daddy.map.dungeon_layout.room_detail_panel import build_room_detail
from dungeon_daddy.map.dungeon_layout.semantics import RoomRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _room(
    id: str = "R1",
    name: str = "Hall",
    note: str = "n",
    layout_role: str | None = None,
    graph_notes: str | None = None,
    visual_priority: str | None = None,
) -> Room:
    return Room(
        id=id, num=1, name=name, x=0, y=0, w=6, h=4, type="hall", note=note,
        layout_role=layout_role, graph_notes=graph_notes, visual_priority=visual_priority,
    )


def _conn(
    from_room: str,
    to_room: str,
    type: str = "door",
    role: str | None = None,
    graph_notes: str | None = None,
) -> Connection:
    return Connection(**{
        "from": from_room,
        "to": to_room,
        "type": type,
        "layout_connection_role": role,
        "graph_notes": graph_notes,
    })


def _level(
    rooms: list[Room],
    connections: list[Connection] | None = None,
    layout_metadata: LayoutMetadata | None = None,
) -> Level:
    return Level(
        id=1, name="Test Level", summary="", ecology="", loop="",
        width=20, height=20, entries=[],
        rooms=rooms, connections=connections or [],
        layout_metadata=layout_metadata,
    )


def _edge(from_room: str, to_room: str) -> RoutedEdge:
    return RoutedEdge(
        connection_id=f"{from_room}→{to_room}",
        points=[(0.0, 0.0), (100.0, 0.0)],
        source_port="right", target_port="left", score=1.0,
    )


def _result(
    room_ids: list[str],
    room_names: dict[str, str] | None = None,
    room_roles: dict[str, RoomRole] | None = None,
    edge_labels: dict[str, str] | None = None,
    edges: list[RoutedEdge] | None = None,
    critical_path: list[str] | None = None,
) -> LayoutResult:
    bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=500.0)
    rooms = {
        rid: RoomRect(room_id=rid, x=float(i * 100), y=0.0, w=80.0, h=50.0)
        for i, rid in enumerate(room_ids)
    }
    return LayoutResult(
        rooms=rooms,
        edges=edges or [],
        labels=[],
        bounds=bounds,
        debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        room_names=room_names or {rid: rid for rid in room_ids},
        room_roles=room_roles or {},
        edge_labels=edge_labels or {},
        critical_path=critical_path or [],
    )


# ---------------------------------------------------------------------------
# Cycle 1 — unknown room_id returns None
# ---------------------------------------------------------------------------

class TestUnknownRoom:
    def test_unknown_room_id_returns_none(self):
        level = _level([_room("R1")])
        result = _result(["R1"])
        assert build_room_detail("UNKNOWN", level, result) is None


# ---------------------------------------------------------------------------
# Cycle 2 — known room populates name and ID
# ---------------------------------------------------------------------------

class TestBasicFields:
    def test_room_id_and_name_populated(self):
        level = _level([_room("R1", name="Receiving Hall")])
        result = _result(["R1"], room_names={"R1": "Receiving Hall"})
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.room_id == "R1"
        assert panel.room_name == "Receiving Hall"

    def test_note_populated(self):
        level = _level([_room("R1", note="A room full of scorpions.")])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.note == "A room full of scorpions."


# ---------------------------------------------------------------------------
# Cycle 3 — role from Room.layout_role
# ---------------------------------------------------------------------------

class TestRoleFromLayoutRole:
    def test_layout_role_used_when_present(self):
        level = _level([_room("R1", layout_role="entrance")])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.role == "entrance"


# ---------------------------------------------------------------------------
# Cycle 4 — role falls back to LayoutResult.room_roles
# ---------------------------------------------------------------------------

class TestRoleFallback:
    def test_role_from_result_when_no_layout_role(self):
        level = _level([_room("R1", layout_role=None)])
        result = _result(["R1"], room_roles={"R1": "hub"})
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.role == "hub"

    def test_role_is_none_when_neither_source_has_role(self):
        level = _level([_room("R1", layout_role=None)])
        result = _result(["R1"], room_roles={})
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.role is None


# ---------------------------------------------------------------------------
# Cycle 5 — on_critical_path from result.critical_path
# ---------------------------------------------------------------------------

class TestCriticalPath:
    def test_on_critical_path_true_when_in_critical_path(self):
        level = _level([_room("R1")])
        result = _result(["R1"], critical_path=["R1", "R2"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.on_critical_path is True

    def test_on_critical_path_false_when_not_in_critical_path(self):
        level = _level([_room("R1")])
        result = _result(["R1"], critical_path=["R2", "R3"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.on_critical_path is False


# ---------------------------------------------------------------------------
# Cycle 6 — connections assembled from level.connections (both directions)
# ---------------------------------------------------------------------------

class TestConnections:
    def test_outgoing_connection_appears_in_panel(self):
        level = _level(
            [_room("R1"), _room("R2", name="Marketplace")],
            connections=[_conn("R1", "R2", type="arch")],
        )
        result = _result(
            ["R1", "R2"],
            room_names={"R1": "Hall", "R2": "Marketplace"},
            edges=[_edge("R1", "R2")],
        )
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert len(panel.connections) == 1
        conn = panel.connections[0]
        assert conn.room_id == "R2"
        assert conn.room_name == "Marketplace"
        assert conn.label == "arch"

    def test_incoming_connection_appears_in_panel(self):
        level = _level(
            [_room("R1"), _room("R2", name="Marketplace")],
            connections=[_conn("R2", "R1", type="door")],
        )
        result = _result(
            ["R1", "R2"],
            room_names={"R1": "Hall", "R2": "Marketplace"},
            edges=[_edge("R2", "R1")],
        )
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert len(panel.connections) == 1
        assert panel.connections[0].room_id == "R2"

    def test_multiple_connections_all_appear(self):
        level = _level(
            [_room("R1"), _room("R2"), _room("R3")],
            connections=[_conn("R1", "R2"), _conn("R1", "R3")],
        )
        result = _result(
            ["R1", "R2", "R3"],
            edges=[_edge("R1", "R2"), _edge("R1", "R3")],
        )
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert len(panel.connections) == 2


# ---------------------------------------------------------------------------
# Cycle 7 — connection role from layout_connection_role
# ---------------------------------------------------------------------------

class TestConnectionRole:
    def test_connection_role_populated(self):
        level = _level(
            [_room("R1"), _room("R2")],
            connections=[_conn("R1", "R2", role="critical_path")],
        )
        result = _result(["R1", "R2"], edges=[_edge("R1", "R2")])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.connections[0].role == "critical_path"

    def test_connection_role_none_when_absent(self):
        level = _level([_room("R1"), _room("R2")], connections=[_conn("R1", "R2")])
        result = _result(["R1", "R2"], edges=[_edge("R1", "R2")])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.connections[0].role is None


# ---------------------------------------------------------------------------
# Cycle 8 — connection graph_notes
# ---------------------------------------------------------------------------

class TestConnectionGraphNotes:
    def test_connection_graph_notes_populated(self):
        level = _level(
            [_room("R1"), _room("R2")],
            connections=[_conn("R1", "R2", graph_notes="Main path to hub.")],
        )
        result = _result(["R1", "R2"], edges=[_edge("R1", "R2")])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.connections[0].graph_notes == "Main path to hub."

    def test_connection_graph_notes_none_when_absent(self):
        level = _level([_room("R1"), _room("R2")], connections=[_conn("R1", "R2")])
        result = _result(["R1", "R2"], edges=[_edge("R1", "R2")])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.connections[0].graph_notes is None


# ---------------------------------------------------------------------------
# Cycle 9 — room graph_notes and visual_priority
# ---------------------------------------------------------------------------

class TestRoomGraphNotes:
    def test_graph_notes_populated(self):
        level = _level([_room("R1", graph_notes="Floor entry point.")])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.graph_notes == "Floor entry point."

    def test_graph_notes_none_when_absent(self):
        level = _level([_room("R1", graph_notes=None)])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.graph_notes is None

    def test_visual_priority_populated(self):
        level = _level([_room("R1", visual_priority="high")])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.visual_priority == "high"

    def test_visual_priority_none_when_absent(self):
        level = _level([_room("R1", visual_priority=None)])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.visual_priority is None


# ---------------------------------------------------------------------------
# Cycle 10 — on_optional_branch from layout_metadata
# ---------------------------------------------------------------------------

class TestOptionalBranch:
    def test_on_optional_branch_true_when_room_in_branch(self):
        meta = LayoutMetadata(optional_branches=[["R2", "R3"]])
        level = _level([_room("R2")], layout_metadata=meta)
        result = _result(["R2"])
        panel = build_room_detail("R2", level, result)
        assert panel is not None
        assert panel.on_optional_branch is True

    def test_on_optional_branch_false_when_room_not_in_any_branch(self):
        meta = LayoutMetadata(optional_branches=[["R2", "R3"]])
        level = _level([_room("R1")], layout_metadata=meta)
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.on_optional_branch is False


# ---------------------------------------------------------------------------
# Cycle 11 — graceful fallback when layout_metadata is absent
# ---------------------------------------------------------------------------

class TestGracefulFallback:
    def test_no_layout_metadata_does_not_raise(self):
        level = _level([_room("R1")], layout_metadata=None)
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.on_optional_branch is False

    def test_missing_role_falls_back_to_none(self):
        level = _level([_room("R1", layout_role=None)])
        result = _result(["R1"], room_roles={})
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.role is None

    def test_no_connections_returns_empty_list(self):
        level = _level([_room("R1")], connections=[])
        result = _result(["R1"])
        panel = build_room_detail("R1", level, result)
        assert panel is not None
        assert panel.connections == []
