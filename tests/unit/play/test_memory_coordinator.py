"""Phase 51.7 Slice 6 — MemoryCoordinator (play/memory_coordinator.py).

Unit tests for the memory seam extracted from ``PlayView``: the ``/remember``
command (``handle_remember``), the silent ``[REMEMBER: …]`` hook
(``auto_remember``) and its marker splitter (``extract_remember``), MEM-panel
population (``load_memory_entries``), commit persistence
(``persist_pending_commit``), and the level-memory overlay's load/save
persistence (``has_level_memory`` / ``load_level_memory`` / ``save_level_memory``).

The coordinator imports no ``arcade`` — it is exercised directly against a real
``DungeonRepository`` + ``MemoryRepository`` + ``PlaySessionContext`` and
recording ports (no PlayView, no window).
"""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.data.models import (
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.memory.models import MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.memory_coordinator import MemoryCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext
from tests.unit.play._factories import MIGRATIONS_DIR


class _Mem:
    """Records every side-effect port call the coordinator makes."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.entries: list[list[MemoryEntry]] = []
        self.refreshes: int = 0
        self.pending: MemoryEntry | None = None

    def post(self, role: str, text: str) -> None:
        self.messages.append((role, text))

    def pop_pending(self) -> MemoryEntry | None:
        commit = self.pending
        self.pending = None
        return commit


def _dungeon() -> Dungeon:
    rooms = [
        Room(id="r1", num=1, name="Entry Hall", x=0, y=0, w=4, h=4, type="hall", note="a"),
        Room(id="r2", num=2, name="North Vault", x=6, y=0, w=4, h=4, type="vault", note="b"),
    ]
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="",
        width=50, height=50, entries=[], rooms=rooms,
        connections=[], loops=[],
    )
    meta = DungeonMeta(title="Crypt", theme="", setting="", party="", quest="")
    return Dungeon(meta=meta, levels=[level])


def _make(
    tmp_path: Path,
    *,
    dungeon: Dungeon | None = None,
    current_room_id: str | None = "r1",
    campaign_id: str | None = "camp-1",
    with_mem_repo: bool = True,
) -> tuple[MemoryCoordinator, _Mem, DungeonRepository, MemoryRepository | None, PlaySessionContext]:
    # The coordinator only touches the level-memory markdown, which is keyed by
    # ``dungeon_id`` — no persisted dungeon file is needed.
    dungeon_repo = DungeonRepository(tmp_path / "saves")

    mem_repo: MemoryRepository | None = None
    if with_mem_repo:
        mem_repo = MemoryRepository(tmp_path / "test.duckdb")
        mem_repo.initialize_schema(MIGRATIONS_DIR)
        mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    dungeon_id = dungeon.meta.title if dungeon is not None else "Crypt"
    session = PlaySessionContext(
        dungeon=dungeon,
        state=SessionState(
            dungeon_id=dungeon_id, current_level_idx=0,
            current_room_id=current_room_id,
            visited_rooms=[current_room_id] if current_room_id else [],
        ),
        mem_repo=mem_repo,
        campaign_id=campaign_id,
    )
    ports = _Mem()
    coord = MemoryCoordinator(
        session,
        post_message=ports.post,
        append_room_event=dungeon_repo.append_room_event,
        load_room_memory=dungeon_repo.load_room_memory,
        save_room_memory=dungeon_repo.save_room_memory,
        set_entries=ports.entries.append,
        pop_pending_commit=ports.pop_pending,
        refresh_memory_state=lambda: setattr(
            ports, "refreshes", ports.refreshes + 1
        ),
    )
    return coord, ports, dungeon_repo, mem_repo, session


# ---------------------------------------------------------------------------
# extract_remember — split a [REMEMBER: …] marker out of DM text
# ---------------------------------------------------------------------------

def test_extract_remember_returns_note_and_cleaned_text(tmp_path):
    coord, _p, _r, _mr, _s = _make(tmp_path, dungeon=_dungeon())

    remembered, cleaned = coord.extract_remember(
        "You find a key. [REMEMBER: the party has the brass key]"
    )

    assert remembered == "the party has the brass key"
    assert cleaned == "You find a key."


def test_extract_remember_no_marker_returns_none_and_original(tmp_path):
    coord, _p, _r, _mr, _s = _make(tmp_path, dungeon=_dungeon())

    remembered, cleaned = coord.extract_remember("Just narration, no marker.")

    assert remembered is None
    assert cleaned == "Just narration, no marker."


# ---------------------------------------------------------------------------
# handle_remember — /remember command
# ---------------------------------------------------------------------------

def test_handle_remember_appends_event_confirms_and_refreshes(tmp_path):
    coord, ports, repo, _mr, session = _make(tmp_path, dungeon=_dungeon())

    coord.handle_remember("a trap sprang here")

    memory = repo.load_room_memory(session.state.dungeon_id, 1)
    assert "a trap sprang here" in memory
    assert "## Room r1 — Entry Hall" in memory
    assert ports.messages == [("system", "Remembered: a trap sprang here")]
    assert ports.refreshes == 1


def test_handle_remember_no_dungeon_warns(tmp_path):
    coord, ports, _r, _mr, _s = _make(tmp_path, dungeon=None)

    coord.handle_remember("nope")

    assert ports.messages == [("system", "No dungeon loaded.")]
    assert ports.refreshes == 0


def test_handle_remember_no_room_warns(tmp_path):
    coord, ports, _r, _mr, _s = _make(
        tmp_path, dungeon=_dungeon(), current_room_id=None
    )

    coord.handle_remember("nope")

    assert ports.messages == [
        ("system", "No room selected — click a room first.")
    ]
    assert ports.refreshes == 0


# ---------------------------------------------------------------------------
# auto_remember — silent [REMEMBER: …] hook
# ---------------------------------------------------------------------------

def test_auto_remember_appends_event_and_notes(tmp_path):
    coord, ports, repo, _mr, session = _make(tmp_path, dungeon=_dungeon())

    coord.auto_remember("the statue turned")

    memory = repo.load_room_memory(session.state.dungeon_id, 1)
    assert "the statue turned" in memory
    assert ports.messages == [("system", "📝 Noted: the statue turned")]
    # auto-remember does NOT trigger the has-memory refresh (unlike /remember)
    assert ports.refreshes == 0


def test_auto_remember_noop_without_room(tmp_path):
    coord, ports, repo, _mr, session = _make(
        tmp_path, dungeon=_dungeon(), current_room_id=None
    )

    coord.auto_remember("ignored")

    assert repo.load_room_memory(session.state.dungeon_id, 1) == ""
    assert ports.messages == []


# ---------------------------------------------------------------------------
# load_memory_entries — populate the MEM panel from the memory store
# ---------------------------------------------------------------------------

def test_load_memory_entries_populates_panel_with_tags(tmp_path):
    coord, ports, _r, mem_repo, _s = _make(tmp_path, dungeon=_dungeon())
    mem_repo.save_memory_entry(
        memory_id="m1", campaign_id="camp-1", entry_type="fact",
        title="The Bargain", summary="A pact was struck.",
        status="approved", importance=7,
    )
    mem_repo.add_memory_tag("m1", "location:entry-hall")
    mem_repo.add_memory_tag("m1", "actor:pc-1")

    coord.load_memory_entries()

    assert len(ports.entries) == 1
    loaded = ports.entries[0]
    assert [e.memory_id for e in loaded] == ["m1"]
    assert loaded[0].title == "The Bargain"
    assert set(loaded[0].tags) == {"location:entry-hall", "actor:pc-1"}


def test_load_memory_entries_noop_without_mem_repo(tmp_path):
    coord, ports, _r, _mr, _s = _make(
        tmp_path, dungeon=_dungeon(), with_mem_repo=False
    )

    coord.load_memory_entries()

    assert ports.entries == []


def test_load_memory_entries_falls_back_to_dungeon_id(tmp_path):
    # No campaign_id → campaign scope falls back to the session dungeon_id.
    coord, ports, _r, mem_repo, session = _make(
        tmp_path, dungeon=_dungeon(), campaign_id=None
    )
    mem_repo.save_campaign(session.state.dungeon_id, "crypt", "Crypt")
    mem_repo.save_memory_entry(
        memory_id="m9", campaign_id=session.state.dungeon_id, entry_type="fact",
        title="Fallback", summary="", status="approved", importance=5,
    )

    coord.load_memory_entries()

    assert [e.memory_id for e in ports.entries[0]] == ["m9"]


# ---------------------------------------------------------------------------
# persist_pending_commit — write a MEM-tab approve/reject to disk
# ---------------------------------------------------------------------------

def test_persist_pending_commit_writes_status(tmp_path):
    coord, ports, _r, mem_repo, _s = _make(tmp_path, dungeon=_dungeon())
    mem_repo.save_memory_entry(
        memory_id="m1", campaign_id="camp-1", entry_type="fact",
        title="T", summary="", status="draft", importance=5,
    )
    ports.pending = MemoryEntry(
        memory_id="m1", campaign_id="camp-1", type="fact",
        title="T", summary="", status="approved", importance=5,
    )

    coord.persist_pending_commit()

    rows = mem_repo.get_memory_entries_by_campaign("camp-1")
    assert rows[0]["status"] == "approved"


def test_persist_pending_commit_noop_when_nothing_pending(tmp_path):
    coord, ports, _r, _mr, _s = _make(tmp_path, dungeon=_dungeon())
    ports.pending = None

    coord.persist_pending_commit()  # must not raise


# ---------------------------------------------------------------------------
# level-memory overlay persistence
# ---------------------------------------------------------------------------

def test_has_level_memory_false_when_empty(tmp_path):
    coord, _p, _r, _mr, _s = _make(tmp_path, dungeon=_dungeon())

    assert coord.has_level_memory() is False


def test_has_level_memory_true_after_write(tmp_path):
    coord, _p, repo, _mr, session = _make(tmp_path, dungeon=_dungeon())
    repo.save_room_memory(session.state.dungeon_id, 1, "# something")

    assert coord.has_level_memory() is True


def test_load_level_memory_returns_level_and_content(tmp_path):
    coord, _p, repo, _mr, session = _make(tmp_path, dungeon=_dungeon())
    repo.save_room_memory(session.state.dungeon_id, 1, "saved notes")

    loaded = coord.load_level_memory()

    assert loaded == (1, "saved notes")


def test_load_level_memory_none_without_dungeon(tmp_path):
    coord, _p, _r, _mr, _s = _make(tmp_path, dungeon=None)

    assert coord.load_level_memory() is None


def test_save_level_memory_persists_content(tmp_path):
    coord, _p, repo, _mr, session = _make(tmp_path, dungeon=_dungeon())

    coord.save_level_memory(1, "edited overlay text")

    assert repo.load_room_memory(session.state.dungeon_id, 1) == "edited overlay text"
