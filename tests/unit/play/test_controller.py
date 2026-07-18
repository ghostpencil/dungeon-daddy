"""Phase 51.7 Slice 7 — PlaySessionController (play/controller.py).

Unit tests for the composition root that wires the five play coordinators
(Action / Navigation / Dialogue / Memory / Narration) + the shared
``PlaySessionContext`` together, and owns the session-facade methods
(session bootstrap + the domain→panel refresh fan-out) extracted from
``PlayView``.

The controller imports no ``arcade`` — it is exercised directly against a
recording *host* (a stand-in for the view exposing the panel widgets + service
handles the coordinator ports read) and real domain objects (``MemoryRepository``,
``PlaySessionContext``). No PlayView, no window.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.actions import ActionOrchestrator
from dungeon_daddy.play.controller import PlaySessionController
from dungeon_daddy.play.dialogue import DialogueCoordinator
from dungeon_daddy.play.memory_coordinator import MemoryCoordinator
from dungeon_daddy.play.narration import NarrationCoordinator
from dungeon_daddy.play.navigation import NavigationCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext
from tests.unit.play._factories import MIGRATIONS_DIR, make_actor


class _RecPanel:
    """A recording widget stub: every call is appended to ``self.calls``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def __getattr__(self, name: str) -> Any:
        def _rec(*args: Any, **kw: Any) -> Any:
            self.calls.append((name, args))
            return None
        return _rec


class _RecChat(_RecPanel):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[tuple[str, str]] = []

    def add_message(self, role: str, text: str) -> None:
        self.messages.append((role, text))


class _StubRepo:
    """Minimal DungeonRepository stand-in for the room-memory + session ports."""

    def __init__(self) -> None:
        self.saved: list[Any] = []

    def load_room_memory(self, dungeon_id: str, level_id: int) -> str:
        return ""

    def save_room_memory(self, dungeon_id: str, level_id: int, content: str) -> None:
        pass

    def load_session(self, save_name: str) -> Any:
        return None

    def save_session(self, state: Any) -> None:
        self.saved.append(state)

    def append_room_event(self, *args: Any) -> None:
        pass


class _Host:
    """Records the panel/service surface the controller's ports read."""

    def __init__(self, *, repo: Any = None) -> None:
        self._chat = _RecChat()
        self._map = _RecPanel()
        self._rpg_scene = _RecPanel()
        self._rpg_vna = _RecPanel()
        self._rpg_action = _RecPanel()
        self._rpg_char = _RecPanel()
        self._rpg_memory = _RecPanel()
        self._rpg_fallout = _RecPanel()
        self._rpg_debug = None
        self._repo = repo
        self._dm_agent = None
        self._rpg_service = None
        self._dungeon_voice_agent = None
        self._action_state = None
        self._portraits_dir: Path | None = None
        self._last_room_context: dict[str, Any] = {}
        self._last_actor_dict: dict[str, Any] = {}
        self._is_test_drive = False
        self._has_memory = False
        self._viewed_level_idx = 0
        self.things_here_pushes = 0
        # Set post-construction; the view-delegator methods below route back into
        # the controller exactly as PlayView's thin delegators do.
        self.controller: Any = None

    def _push_things_here_overlay(self) -> None:
        self.things_here_pushes += 1

    def _load_player_actors(self) -> None:
        if self.controller is not None:
            self.controller.load_player_actors()

    def _refresh_vna_panel(self) -> None:
        if self.controller is not None:
            self.controller.refresh_vna_panel()


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
) -> tuple[PlaySessionController, _Host, PlaySessionContext, MemoryRepository]:
    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")
    session = PlaySessionContext(
        dungeon=dungeon,
        state=SessionState(
            dungeon_id="d1", current_level_idx=0,
            current_room_id="r1", visited_rooms=["r1"],
        ),
        mem_repo=mem_repo,
        campaign_id="camp-1",
    )
    host = _Host(repo=_StubRepo())
    controller = PlaySessionController(host, session=session)
    host.controller = controller
    return controller, host, session, mem_repo


def test_controller_exposes_five_coordinators_sharing_the_context(tmp_path: Path) -> None:
    controller, _host, session, _repo = _make(tmp_path, dungeon=_dungeon())

    assert controller.context is session
    assert isinstance(controller.narration, NarrationCoordinator)
    assert isinstance(controller.dialogue, DialogueCoordinator)
    assert isinstance(controller.actions, ActionOrchestrator)
    assert isinstance(controller.navigation, NavigationCoordinator)
    assert isinstance(controller.memory, MemoryCoordinator)
    # Every coordinator shares the one context instance.
    assert controller.narration._session is session
    assert controller.navigation._session is session
    assert controller.memory._session is session


def test_set_debug_lookups_routes_to_debug_panel(tmp_path: Path) -> None:
    from dungeon_daddy.llm.lookup_tool import LookupRecord

    controller, host, _session, _repo = _make(tmp_path, dungeon=_dungeon())
    host._rpg_debug = _RecPanel()
    recs = [LookupRecord(query="mira", hit_count=1)]

    controller._set_debug_lookups(recs)

    assert ("set_lookups", (recs,)) in host._rpg_debug.calls


def test_set_debug_lookups_noop_without_debug_panel(tmp_path: Path) -> None:
    from dungeon_daddy.llm.lookup_tool import LookupRecord

    controller, host, _session, _repo = _make(tmp_path, dungeon=_dungeon())
    assert host._rpg_debug is None
    # No panel → no crash.
    controller._set_debug_lookups([LookupRecord(query="mira")])


def test_set_debug_bundle_noop_on_new_built_host(tmp_path: Path) -> None:
    # Cleanup item 11.2: _set_debug_bundle fires from on_bundle_built during
    # narration; like its sibling _set_debug_lookups it must tolerate a
    # __new__-built host that never ran PlayView.__init__ (so `_rpg_debug` was
    # never set) — a missing attr, not just a None panel. Guard with getattr.
    from dungeon_daddy.memory.models import ContextBundle

    controller, host, _session, _repo = _make(tmp_path, dungeon=_dungeon())
    del host._rpg_debug
    assert not hasattr(host, "_rpg_debug")
    bundle = ContextBundle(bundle_id="b", campaign_id="camp-1", mode="run_scene")

    # No _rpg_debug attribute → must not raise (matches _set_debug_lookups).
    controller._set_debug_bundle(bundle)


def test_set_debug_bundle_routes_to_debug_panel(tmp_path: Path) -> None:
    from dungeon_daddy.memory.models import ContextBundle

    controller, host, _session, _repo = _make(tmp_path, dungeon=_dungeon())
    host._rpg_debug = _RecPanel()
    bundle = ContextBundle(bundle_id="b", campaign_id="camp-1", mode="run_scene")

    controller._set_debug_bundle(bundle)

    assert ("set_bundle", (bundle,)) in host._rpg_debug.calls


def test_narration_on_lookups_port_wired_to_controller(tmp_path: Path) -> None:
    from dungeon_daddy.llm.lookup_tool import LookupRecord

    controller, host, _session, _repo = _make(tmp_path, dungeon=_dungeon())
    host._rpg_debug = _RecPanel()
    recs = [LookupRecord(query="mira", hit_count=1)]

    # The port the coordinator was constructed with routes to the debug panel.
    controller.narration._on_lookups(recs)

    assert ("set_lookups", (recs,)) in host._rpg_debug.calls


def test_load_dungeon_transient_sets_context_and_posts_dm_line(tmp_path: Path) -> None:
    controller, host, session, _repo = _make(tmp_path)

    controller.load_dungeon_transient(_dungeon())

    assert host._is_test_drive is True
    assert session.dungeon is not None
    assert session.state is not None
    assert session.state.dungeon_id == "__test_drive__"
    # The "Loaded …" DM line lands on the chat panel.
    assert any(role == "dm" and "Level 1" in text for role, text in host._chat.messages)
    # Loop chips are the test-drive affordance.
    assert ("set_loops_visible", (True,)) in host._map.calls


def test_save_session_persists_only_when_not_test_drive(tmp_path: Path) -> None:
    class _Repo:
        def __init__(self) -> None:
            self.saved: list[Any] = []

        def save_session(self, state: Any) -> None:
            self.saved.append(state)

    repo = _Repo()
    controller, host, session, _mem = _make(tmp_path)
    host._repo = repo

    host._is_test_drive = True
    controller.save_session()
    assert repo.saved == []  # test drive never persists

    host._is_test_drive = False
    controller.save_session()
    assert repo.saved == [session.state]


def test_refresh_memory_state_caches_flag_on_host(tmp_path: Path) -> None:
    controller, host, _session, _repo = _make(tmp_path, dungeon=_dungeon())
    # No level memory seeded → flag is False.
    controller.refresh_memory_state()
    assert host._has_memory is False


def test_acting_actor_prefers_selected_then_first(tmp_path: Path) -> None:
    controller, host, session, _repo = _make(tmp_path)
    a1 = make_actor(actor_id="pc-1", slug="elara", display_name="Elara")
    a2 = make_actor(actor_id="pc-2", slug="brakk", display_name="Brakk")
    session.set_actors([a1, a2])

    class _AS:
        actor_id: str | None = "pc-2"

    host._action_state = _AS()
    assert controller.acting_actor() is a2
    host._action_state.actor_id = None
    assert controller.acting_actor() is a1
