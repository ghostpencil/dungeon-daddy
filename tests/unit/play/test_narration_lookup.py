"""Slice B4d — NarrationCoordinator wires the `lookup_world` executor (spec §10).

``spawn_dm_thread`` builds a read-only ``LookupService`` executor from the
session's repo + the scene bundle's entity ids and hands it to the DM agent's
``lookup`` seam. The executor reaches the campaign DB (search_entities under the
L5 read lock); with no repo, the seam is ``None`` (agent falls back to
``complete``).
"""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.llm.provider import LLMToolCall
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.narration import NarrationCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "dungeon_daddy" / "data" / "migrations"
)


def _dungeon() -> Dungeon:
    rooms = [Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")]
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="lock_key",
        width=12, height=10, entries=[], rooms=rooms,
        connections=[Connection(from_room="1-A", to_room="1-A", type="door")],
    )
    return Dungeon(meta=DungeonMeta(title="T", theme="", setting="", party="", quest=""), levels=[level])


class _StubAgent:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def respond(self, **kwargs) -> str:  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        return "ok"


class _LookupCallingAgent:
    """A DM agent whose respond() invokes the injected lookup executor once
    (simulating a `lookup_world` tool call) so a LookupRecord is produced."""

    def respond(self, **kwargs) -> str:  # type: ignore[no-untyped-def]
        lookup = kwargs.get("lookup")
        if lookup is not None:
            lookup(LLMToolCall("c1", "lookup_world", {"query": "mira"}))
        return "ok"


class _StubRepo:
    def load_room_memory(self, dungeon_id: str, level_id: int) -> str:
        return "prior events"


def _coord(
    mem_repo: MemoryRepository | None,
    agent,  # type: ignore[no-untyped-def]
    on_lookups=None,  # type: ignore[no-untyped-def]
    campaign_id: str | None = "camp-1",
) -> NarrationCoordinator:
    session = PlaySessionContext(
        dungeon=_dungeon(),
        state=SessionState(dungeon_id="d", current_level_idx=0, current_room_id="1-A"),
        mem_repo=mem_repo,
        campaign_id=campaign_id,
    )
    return NarrationCoordinator(
        session,
        get_dm_agent=lambda: agent,
        get_repo=lambda: _StubRepo(),
        get_rpg_service=lambda: None,
        on_busy=lambda b: None,
        post_dm=lambda s: None,
        post_system=lambda s: None,
        on_dungeon_reply=lambda pm, c: None,
        extract_remember=lambda t: (None, t),
        auto_remember=lambda s: None,
        on_lookups=on_lookups,
    )


def test_spawn_passes_working_lookup_executor_to_agent() -> None:
    repo = MemoryRepository(db_path=Path(":memory:"))
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_actor("npc-mira", "camp-1", "npc", "mira", "Mira", tags=["actor:npc:mira"])
    agent = _StubAgent()
    coord = _coord(repo, agent)

    room = _dungeon().levels[0].rooms[0]
    level = _dungeon().levels[0]
    coord.spawn_dm_thread(room, level)
    assert coord.active_thread is not None
    coord.active_thread.join(timeout=5.0)

    lookup = agent.calls[0]["lookup"]
    assert callable(lookup)
    payload = json.loads(lookup(LLMToolCall("c1", "lookup_world", {"query": "mira"})))
    assert payload["results"][0]["id"] == "npc-mira"


def test_lookup_is_none_without_repo() -> None:
    agent = _StubAgent()
    coord = _coord(None, agent)

    room = _dungeon().levels[0].rooms[0]
    level = _dungeon().levels[0]
    coord.spawn_dm_thread(room, level)
    assert coord.active_thread is not None
    coord.active_thread.join(timeout=5.0)

    assert agent.calls[0]["lookup"] is None


def test_lookup_is_none_without_active_campaign() -> None:
    # Cleanup item 8: a repo present but no campaign_id means no active campaign.
    # Narration must treat that as inactive (no lookup seam) — matching
    # DialogueCoordinator's ``active_campaign()`` gate — not silently scope the
    # LookupService to ``state.dungeon_id`` (a dungeon id, wrong namespace) and
    # return an executor that queries a campaign that isn't there.
    repo = MemoryRepository(db_path=Path(":memory:"))
    repo.initialize_schema(MIGRATIONS_DIR)
    agent = _StubAgent()
    coord = _coord(repo, agent, campaign_id=None)

    room = _dungeon().levels[0].rooms[0]
    level = _dungeon().levels[0]
    coord.spawn_dm_thread(room, level)
    assert coord.active_thread is not None
    coord.active_thread.join(timeout=5.0)

    assert agent.calls[0]["lookup"] is None


# -- Slice B4e — lookup provenance rides back to the main thread -------------


def test_spawn_attaches_lookup_records_to_result() -> None:
    repo = MemoryRepository(db_path=Path(":memory:"))
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_actor("npc-mira", "camp-1", "npc", "mira", "Mira", tags=["actor:npc:mira"])
    coord = _coord(repo, _LookupCallingAgent())

    room = _dungeon().levels[0].rooms[0]
    level = _dungeon().levels[0]
    coord.spawn_dm_thread(room, level)
    assert coord.active_thread is not None
    coord.active_thread.join(timeout=5.0)

    result = coord.queue.get_nowait()
    assert len(result.lookups) == 1
    assert result.lookups[0].query == "mira"
    assert result.lookups[0].hit_count == 1


def test_poll_forwards_lookups_to_port() -> None:
    from dungeon_daddy.llm.lookup_tool import LookupRecord
    from dungeon_daddy.play.narration import DMResult

    got: list[list[LookupRecord]] = []
    coord = _coord(None, _StubAgent(), on_lookups=got.append)
    rec = LookupRecord(query="mira", hit_count=1)
    coord.queue.put(DMResult(content="hi", lookups=[rec]))

    coord.poll()

    assert got == [[rec]]


def test_poll_forwards_empty_lookups_to_clear_the_panel() -> None:
    # A lookup-free turn must clear the panel: otherwise a record from an
    # earlier turn keeps rendering and reads as provenance for *this*
    # narration. Most turns call no tool, so stale is the common case.
    from dungeon_daddy.llm.lookup_tool import LookupRecord
    from dungeon_daddy.play.narration import DMResult

    got: list[list[LookupRecord]] = []
    coord = _coord(None, _StubAgent(), on_lookups=got.append)
    coord.queue.put(DMResult(content="hi"))

    coord.poll()

    assert got == [[]]
