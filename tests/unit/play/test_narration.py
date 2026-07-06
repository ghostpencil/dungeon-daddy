"""Unit tests for :class:`NarrationCoordinator` (Phase 51.7, Slice 2).

The coordinator owns the DM-narration plumbing extracted from ``PlayView``:
history + compaction, the worker-thread spawn, and the thread-safe result queue
+ busy flag. It collapses the 8× narration-entry idiom into
``request_narration`` and drains its own queue via ``poll``.

Real objects throughout (no arcade needed): a real ``PlaySessionContext`` with a
real ``Dungeon``/``SessionState``, a tiny stub DM agent for the LLM seam (the
one mandatory boundary), and plain-callable ports capturing side effects.
"""
from __future__ import annotations

from dungeon_daddy.data.models import (
    Connection,
    Dungeon,
    DungeonMeta,
    Level,
    Room,
    SessionState,
)
from dungeon_daddy.play.narration import DMResult, NarrationCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext


def _dungeon() -> Dungeon:
    rooms = [Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")]
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="lock_key",
        width=12, height=10, entries=[], rooms=rooms,
        connections=[Connection(from_room="1-A", to_room="1-A", type="door")],
    )
    return Dungeon(
        meta=DungeonMeta(title="T", theme="", setting="", party="", quest=""),
        levels=[level],
    )


class _StubAgent:
    """Records the call and returns a canned reply (the DM-agent LLM seam)."""

    def __init__(self, reply: str = "The torches gutter.") -> None:
        self.reply = reply
        self.calls: list[dict] = []

    def respond(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.reply


class _StubRepo:
    def load_room_memory(self, dungeon_id: str, level_id: int) -> str:
        return "prior events"


class _Ports:
    """Collects everything the coordinator's ports emit, for assertions."""

    def __init__(self) -> None:
        self.busy: list[bool] = []
        self.dm: list[str] = []
        self.system: list[str] = []
        self.dungeon: list[tuple[str, str]] = []
        self.auto_remembered: list[str] = []
        self.remember_map: dict[str, tuple[str | None, str]] = {}

    def extract_remember(self, text: str) -> tuple[str | None, str]:
        return self.remember_map.get(text, (None, text))


def _make(*, agent=None, repo=None, rpg_service=None, current_room_id="1-A"):
    session = PlaySessionContext(
        dungeon=_dungeon(),
        state=SessionState(dungeon_id="d", current_level_idx=0, current_room_id=current_room_id),
        campaign_id="camp-1",
    )
    ports = _Ports()
    coord = NarrationCoordinator(
        session,
        get_dm_agent=lambda: agent,
        get_repo=lambda: repo,
        get_rpg_service=lambda: rpg_service,
        on_busy=ports.busy.append,
        post_dm=ports.dm.append,
        post_system=ports.system.append,
        on_dungeon_reply=lambda pm, c: ports.dungeon.append((pm, c)),
        extract_remember=ports.extract_remember,
        auto_remember=ports.auto_remembered.append,
    )
    return coord, session, ports


# -- request_narration --------------------------------------------------------

def test_request_narration_appends_user_turn_sets_busy_and_spawns() -> None:
    agent = _StubAgent(reply="Dust settles.")
    coord, _session, ports = _make(agent=agent, repo=_StubRepo())

    coord.request_narration("Elara [SENSE] search — FULL")

    assert coord.history[-1].role == "user"
    assert coord.history[-1].content == "Elara [SENSE] search — FULL"
    assert ports.busy == [True]
    assert coord.active_thread is not None
    coord.active_thread.join(timeout=5.0)
    # The worker enqueued the DM reply; the agent saw the room/level.
    assert agent.calls and agent.calls[0]["room"].id == "1-A"
    result = coord.queue.get_nowait()
    assert result.content == "Dust settles."


def test_request_narration_no_op_without_current_room() -> None:
    coord, _session, ports = _make(agent=_StubAgent(), repo=_StubRepo(), current_room_id=None)

    coord.request_narration("hello")

    assert coord.history == []
    assert ports.busy == []
    assert coord.active_thread is None


# -- poll routing -------------------------------------------------------------

def test_poll_narration_appends_assistant_displays_and_clears_busy() -> None:
    coord, _session, ports = _make()
    coord.is_busy = True
    coord.queue.put(DMResult(content="You see a door."))

    coord.poll()

    assert coord.is_busy is False
    assert ports.busy == [False]
    assert coord.history[-1].role == "assistant"
    assert coord.history[-1].content == "You see a door."
    assert ports.dm == ["You see a door."]
    assert ports.auto_remembered == []


def test_poll_extracts_remember_and_auto_remembers() -> None:
    coord, _session, ports = _make()
    ports.remember_map["raw <<x>>"] = ("x", "clean")
    coord.queue.put(DMResult(content="raw <<x>>"))

    coord.poll()

    assert coord.history[-1].content == "clean"
    assert ports.dm == ["clean"]
    assert ports.auto_remembered == ["x"]


def test_poll_error_posts_system_line() -> None:
    coord, _session, ports = _make()
    coord.is_busy = True
    coord.queue.put(DMResult(content="", error="API timeout"))

    coord.poll()

    assert coord.is_busy is False
    assert ports.system == ["⚠ The dungeon is silent. (API timeout)"]
    assert ports.dm == []


def test_poll_dungeon_routes_to_dungeon_reply() -> None:
    coord, _session, ports = _make()
    coord.queue.put(
        DMResult(content="I remember.", dungeon=True, player_message="do you recall?")
    )

    coord.poll()

    assert ports.dungeon == [("do you recall?", "I remember.")]
    assert ports.dm == []


def test_poll_empty_queue_is_a_no_op() -> None:
    coord, _session, ports = _make()
    coord.poll()
    assert ports.busy == []
    assert coord.history == []


# -- compaction ---------------------------------------------------------------

def test_compact_history_drops_oldest_pairs_over_budget() -> None:
    from dungeon_daddy.llm.provider import LLMMessage

    coord, _session, _ports = _make()
    big = "x" * 4001  # ~1000 tokens each; two pairs (4) exceed the 2000 budget
    coord.history = [LLMMessage(role="user" if i % 2 == 0 else "assistant", content=big) for i in range(4)]

    coord.compact_history()

    assert len(coord.history) == 2  # one pair dropped


# -- spawn guards -------------------------------------------------------------

def test_spawn_dm_thread_dropped_when_busy() -> None:
    agent = _StubAgent()
    coord, _session, _ports = _make(agent=agent, repo=_StubRepo())
    coord.is_busy = True

    coord.spawn_dm_thread(_dungeon().levels[0].rooms[0], _dungeon().levels[0])

    assert coord.active_thread is None
    assert agent.calls == []


def test_spawn_dm_thread_without_agent_queues_error() -> None:
    coord, _session, _ports = _make(agent=None, repo=_StubRepo())

    coord.spawn_dm_thread(_dungeon().levels[0].rooms[0], _dungeon().levels[0])

    result = coord.queue.get_nowait()
    assert result.error is not None
    assert "DM agent unavailable" in result.error


# -- build_context_bundle -----------------------------------------------------

def test_build_context_bundle_none_without_rpg_service() -> None:
    coord, _session, _ports = _make(rpg_service=None)
    assert coord.build_context_bundle() is None


# -- spawn (dungeon-voice channel) --------------------------------------------

def test_spawn_runs_worker_enqueues_result_and_clears_busy() -> None:
    coord, _session, _ports = _make()

    def _worker() -> DMResult:
        return DMResult(content="reply", dungeon=True, player_message="q")

    coord.spawn(_worker)
    assert coord.active_thread is not None
    coord.active_thread.join(timeout=5.0)

    assert coord.is_busy is False
    result = coord.queue.get_nowait()
    assert result.content == "reply"
    assert result.dungeon is True


def test_spawn_dropped_when_busy() -> None:
    coord, _session, _ports = _make()
    coord.is_busy = True
    ran = []

    coord.spawn(lambda: ran.append(1) or DMResult(content=""))

    assert coord.active_thread is None
    assert ran == []
