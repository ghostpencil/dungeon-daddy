"""Phase 51.7 Slice 5 — NavigationCoordinator (play/navigation.py).

Unit tests for the navigation seam extracted from ``PlayView``: exit moves
(``on_exit_move``), the graph room-select branch (``on_graph_room_select``),
party-room focus on load/resume (``focus_party_room``), and the layout-label
helpers (``current_level_rooms`` / ``prepare_vna_exits``). The coordinator
imports no ``arcade`` — it is exercised directly against a real
``MemoryRepository`` + ``PlaySessionContext`` and recording ports (no PlayView,
no window).
"""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.navigation import NavigationCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext
from dungeon_daddy.rpg.models import RoomExit
from tests.unit.play._factories import MIGRATIONS_DIR


class _Nav:
    """Records every side-effect port call the coordinator makes."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.narration_requests: list[str] = []
        self.selected_rooms: list[str] = []
        self.current_rooms: list[tuple[str, str, str]] = []
        self.scenes: list[tuple[str, str]] = []
        self.map_loads: list[tuple[object, object, int]] = []
        self.map_updates: list[tuple[object, int]] = []
        self.viewed_levels: list[int] = []
        self.dialogue_ends: int = 0
        self.vna_refreshes: int = 0
        self.saves: int = 0

    def post(self, role: str, text: str) -> None:
        self.messages.append((role, text))


def _dungeon() -> Dungeon:
    rooms = [
        Room(id="r1", num=1, name="Entry Hall", x=0, y=0, w=4, h=4, type="hall", note="a"),
        Room(id="r2", num=2, name="North Vault", x=6, y=0, w=4, h=4, type="vault", note="b"),
    ]
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="",
        width=50, height=50, entries=[], rooms=rooms,
        connections=[Connection(from_room="r1", to_room="r2", type="door")], loops=[],
    )
    meta = DungeonMeta(title="T", theme="", setting="", party="", quest="")
    return Dungeon(meta=meta, levels=[level])


def _make(
    tmp_path: Path,
    *,
    dungeon: Dungeon | None = None,
    current_room_id: str = "r1",
) -> tuple[NavigationCoordinator, _Nav, MemoryRepository, PlaySessionContext]:
    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    session = PlaySessionContext(
        dungeon=dungeon,
        state=SessionState(
            dungeon_id="d1", current_level_idx=0,
            current_room_id=current_room_id, visited_rooms=[current_room_id],
        ),
        mem_repo=mem_repo,
        campaign_id="camp-1",
    )
    nav_ports = _Nav()
    coord = NavigationCoordinator(
        session,
        post_message=nav_ports.post,
        request_narration=nav_ports.narration_requests.append,
        set_selected_room=nav_ports.selected_rooms.append,
        set_current_room=lambda name, note, room_id: nav_ports.current_rooms.append(
            (name, note, room_id)
        ),
        set_scene=lambda name, level_id: nav_ports.scenes.append((name, level_id)),
        load_level=lambda level, state, total: nav_ports.map_loads.append(
            (level, state, total)
        ),
        update_map_state=lambda state, total: nav_ports.map_updates.append(
            (state, total)
        ),
        set_viewed_level=nav_ports.viewed_levels.append,
        end_dialogue_on_room_change=lambda: setattr(
            nav_ports, "dialogue_ends", nav_ports.dialogue_ends + 1
        ),
        refresh_vna_panel=lambda: setattr(
            nav_ports, "vna_refreshes", nav_ports.vna_refreshes + 1
        ),
        save_session=lambda: setattr(nav_ports, "saves", nav_ports.saves + 1),
    )
    return coord, nav_ports, mem_repo, session


def _save_exit(repo: MemoryRepository, **kw) -> RoomExit:
    defaults = dict(
        exit_id="e1", campaign_id="camp-1",
        from_room_id="r1", to_room_id="r2", level_id="level-1",
        label="North Door", exit_type="door", status="open",
    )
    defaults.update(kw)
    ex = RoomExit(**defaults)
    repo.save_room_exit(ex)
    return ex


# ---------------------------------------------------------------------------
# current_level_rooms — layout geometry lookup for exit compass labels
# ---------------------------------------------------------------------------

def test_current_level_rooms_no_dungeon_returns_empty(tmp_path):
    coord, _nav, _repo, _session = _make(tmp_path, dungeon=None)

    rooms_by_id, from_room = coord.current_level_rooms("r1")

    assert rooms_by_id == {}
    assert from_room is None


# ---------------------------------------------------------------------------
# prepare_vna_exits — surface only player-known exits, with labels
# ---------------------------------------------------------------------------

def test_prepare_vna_exits_drops_unknown_and_labels_known(tmp_path):
    coord, _nav, _repo, _session = _make(tmp_path, dungeon=_dungeon())
    room_context = {
        "exits": [
            {"exit_id": "e1", "to_room_id": "r2", "exit_type": "door", "status": "open"},
            {"exit_id": "e2", "to_room_id": "r2", "exit_type": "door", "status": "hidden"},
        ],
    }

    prepared = coord.prepare_vna_exits(room_context, "r1")

    exits = prepared["exits"]
    assert [e["exit_id"] for e in exits] == ["e1"]
    assert exits[0]["label"]


# ---------------------------------------------------------------------------
# focus_party_room — reflect the saved party room in map + side panels
# ---------------------------------------------------------------------------

def test_focus_party_room_sets_map_selection_and_panels(tmp_path):
    coord, nav, _repo, _session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r2")

    coord.focus_party_room()

    assert nav.selected_rooms == ["r2"]
    assert nav.current_rooms == [("North Vault", "b", "r2")]
    assert nav.scenes == [("North Vault", "1")]


def test_focus_party_room_noop_when_no_current_room(tmp_path):
    coord, nav, _repo, session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r1")
    session.state.current_room_id = None

    coord.focus_party_room()

    assert nav.selected_rooms == []
    assert nav.current_rooms == []
    assert nav.scenes == []


# ---------------------------------------------------------------------------
# on_graph_room_select — enter a room by clicking it on the graph
# ---------------------------------------------------------------------------

def test_on_graph_room_select_enters_room_and_narrates(tmp_path):
    coord, nav, _repo, session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r1")

    coord.on_graph_room_select("r2")

    assert session.state.current_room_id == "r2"
    assert "r2" in session.state.visited_rooms
    assert nav.map_updates == [(session.state, 1)]
    assert nav.current_rooms == [("North Vault", "b", "r2")]
    assert nav.scenes == [("North Vault", "1")]
    assert nav.narration_requests == ["We enter North Vault."]
    assert nav.saves == 1


def test_on_graph_room_select_unknown_room_is_noop(tmp_path):
    coord, nav, _repo, session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r1")

    coord.on_graph_room_select("nope")

    assert session.state.current_room_id == "r1"
    assert nav.map_updates == []
    assert nav.saves == 0


# ---------------------------------------------------------------------------
# on_exit_move — apply an engine-validated party move, then narrate
# ---------------------------------------------------------------------------

def test_on_exit_move_accept_updates_state_map_and_narrates(tmp_path):
    coord, nav, repo, session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r1")
    _save_exit(repo, status="open")

    coord.on_exit_move("e1", "cautiously")

    assert session.state.current_room_id == "r2"
    assert "r2" in session.state.visited_rooms
    assert nav.dialogue_ends == 1
    # same level → update_state (not load), selection + panels follow the party
    assert nav.map_updates == [(session.state, 1)]
    assert nav.map_loads == []
    assert nav.selected_rooms == ["r2"]
    assert nav.current_rooms == [("North Vault", "b", "r2")]
    assert nav.scenes == [("North Vault", "1")]
    assert nav.vna_refreshes == 1
    assert nav.saves == 1
    # Narration echoes the move + the mover's sorted modifier flags verbatim.
    assert len(nav.narration_requests) == 1
    msg = nav.narration_requests[0]
    assert msg.startswith("We move cautiously through the exit into North Vault. (effects: ")
    assert "suppress_entry_ticks" in msg


def test_on_exit_move_rejected_keeps_room_and_warns(tmp_path):
    coord, nav, repo, session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r1")
    _save_exit(repo, status="locked", requires_item_slug="iron-key")

    coord.on_exit_move("e1", "cautiously")

    assert session.state.current_room_id == "r1"
    assert len(nav.messages) == 1
    role, text = nav.messages[0]
    assert role == "system"
    assert text.startswith("⚠ Can't move:")
    assert nav.saves == 0
    assert nav.narration_requests == []


def test_on_exit_move_noop_without_repo(tmp_path):
    coord, nav, _repo, session = _make(tmp_path, dungeon=_dungeon(), current_room_id="r1")
    session.mem_repo = None

    coord.on_exit_move("e1", "cautiously")

    assert session.state.current_room_id == "r1"
    assert nav.messages == []
    assert nav.saves == 0
