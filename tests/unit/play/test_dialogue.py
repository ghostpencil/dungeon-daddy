"""Phase 51.7 Slice 3 — DialogueCoordinator (play/dialogue.py).

Unit tests for the dialogue seam extracted from ``PlayView``: the open-channel
``DialogueSession``, begin/end + room-change close, dungeon/NPC line routing, the
``agent_inputs`` §4.4 context assembly, and ``apply_dungeon_reply`` engine
side-effect. The coordinator imports no ``arcade`` — it is exercised directly
against a real ``MemoryRepository`` + ``PlaySessionContext`` and a recording chat
port (no PlayView, no window).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.dialogue import DialogueCoordinator, DialogueSession
from dungeon_daddy.play.narration import DMResult
from dungeon_daddy.play.session_context import PlaySessionContext
from dungeon_daddy.rpg.models import ActorState

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)


def _actor(**kw) -> ActorState:
    defaults = dict(
        actor_id="pc-1", campaign_id="camp-1", actor_type="pc",
        slug="elara", display_name="Elara", status="active",
        actions={"fight": 2, "sense": 1}, playbook_slug="fighter",
    )
    defaults.update(kw)
    return ActorState(**defaults)


class _Chat:
    """Records the chat-port calls the coordinator makes."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.dialogue_mode: bool | None = None
        self.busy: bool | None = None

    def post(self, role: str, text: str) -> None:
        self.messages.append((role, text))

    def set_dialogue_mode(self, on: bool) -> None:
        self.dialogue_mode = on

    def set_busy(self, on: bool) -> None:
        self.busy = on


class _FakeNarration:
    """Minimal stand-in for NarrationCoordinator: busy flag + captured worker."""

    def __init__(self, busy: bool = False) -> None:
        self.is_busy = busy
        self.worker: Any = None

    def spawn(self, worker) -> None:
        self.worker = worker


class _FakeProvider:
    def __init__(self, reply: str = "I have watched you a long time.") -> None:
        self.reply = reply
        self.calls: list[dict] = []

    def complete(self, *, messages, system, max_tokens):
        self.calls.append({"messages": messages, "system": system})
        return self.reply


def _make(
    tmp_path: Path,
    *,
    actor: ActorState | None = None,
    room_context: dict[str, Any] | None = None,
    voice_agent: Any = None,
    narration: _FakeNarration | None = None,
    dungeon: Any = None,
) -> tuple[DialogueCoordinator, _Chat, MemoryRepository, PlaySessionContext, _FakeNarration]:
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
        actors=[actor or _actor()],
    )
    chat = _Chat()
    narr = narration or _FakeNarration()
    coord = DialogueCoordinator(
        session,
        get_narration=lambda: narr,
        get_voice_agent=lambda: voice_agent,
        get_acting_actor=lambda: session.acting_actor(),
        post_message=chat.post,
        set_dialogue_mode=chat.set_dialogue_mode,
        set_busy=chat.set_busy,
        get_room_context=lambda: room_context or {},
    )
    return coord, chat, mem_repo, session, narr


def _seed_intimacy_clock(repo, *, filled, segments, campaign_id="camp-1"):
    repo.save_clock(
        clock_id="intimacy-1", campaign_id=campaign_id,
        label="Dungeon Intimacy", segments=segments, filled=filled,
        clock_level="dungeon", category="dungeon_intimacy", monotonic=False,
    )


def _save_subsystem(repo, *, slug, name, archetype, state, campaign_id="camp-1"):
    from dungeon_daddy.rpg.models import RoomObject

    repo.save_room_object(
        RoomObject(
            object_id=f"obj-{slug}", campaign_id=campaign_id, room_id="r1",
            level_id="l1", slug=slug, display_name=name, archetype=archetype,
            description="A dungeon subsystem.", current_state=state,
        )
    )


def _save_objective(repo, *, slug, tier, status, knowledge=None,
                    description="Restore the loop.", campaign_id="camp-1"):
    from dungeon_daddy.rpg.models import Objective, ObjectiveCompletion

    repo.save_objective(
        Objective(
            objective_id=f"obj:{slug}", campaign_id=campaign_id, slug=slug,
            title=slug.replace("-", " ").title(), description=description,
            tier_index=tier, status=status,
            completion=ObjectiveCompletion(
                kind="object_state", target_slug="x", required_state="restored",
            ),
            advances_clock_slug="dungeon_intimacy",
            reveals_knowledge=knowledge or [],
        )
    )


def _dungeon_model(room_labels):
    from types import SimpleNamespace

    by_level: dict = {}
    for room_id, (level_id, room_name) in room_labels.items():
        by_level.setdefault(level_id, []).append(
            SimpleNamespace(id=room_id, name=room_name)
        )
    levels = [SimpleNamespace(id=lid, rooms=rooms) for lid, rooms in by_level.items()]
    return SimpleNamespace(levels=levels)


# ---------------------------------------------------------------------------
# begin / end / room-change close
# ---------------------------------------------------------------------------

def test_begin_dialogue_opens_npc_session(tmp_path):
    coord, chat, *_ = _make(tmp_path)

    coord.begin_dialogue(kind="npc", room_id="r1", target_id="npc-1",
                         opener="You open a conversation with the Warden.")

    assert coord.session is not None
    assert coord.session.kind == "npc"
    assert coord.session.target_id == "npc-1"
    assert coord.session.room_id == "r1"
    assert chat.dialogue_mode is True
    assert ("system", "You open a conversation with the Warden.") in chat.messages


def test_end_dialogue_closes_channel(tmp_path):
    coord, chat, *_ = _make(tmp_path)
    coord.session = DialogueSession(kind="npc", room_id="r1", target_id="npc-1")

    coord.end_dialogue()

    assert coord.session is None
    assert chat.dialogue_mode is False


def test_leave_command_closes_dialogue(tmp_path):
    coord, chat, *_ = _make(tmp_path)
    coord.session = DialogueSession(kind="npc", room_id="r1", target_id="npc-1")

    coord.send_line("/leave")

    assert coord.session is None
    assert chat.dialogue_mode is False


def test_npc_line_records_turn_and_stays_open(tmp_path):
    coord, chat, *_ = _make(tmp_path)
    coord.session = DialogueSession(kind="npc", room_id="r1", target_id="npc-1")

    coord.send_line("well met")

    assert coord.session is not None
    assert ("player", "well met") in coord.session.turns
    assert ("gm", "well met") in chat.messages
    assert chat.dialogue_mode is None  # not toggled


def test_room_change_closes_open_dialogue(tmp_path):
    coord, chat, _repo, session, _ = _make(tmp_path)
    coord.session = DialogueSession(kind="dungeon", room_id="r1")
    session.state.current_room_id = "r2"  # party has left the resonance room

    coord.maybe_end_on_room_change()

    assert coord.session is None
    assert chat.dialogue_mode is False


def test_dialogue_stays_open_in_same_room(tmp_path):
    coord, chat, *_ = _make(tmp_path)
    coord.session = DialogueSession(kind="dungeon", room_id="r1")  # still in r1

    coord.maybe_end_on_room_change()

    assert coord.session is not None
    assert chat.dialogue_mode is None


# ---------------------------------------------------------------------------
# intimacy clock + dungeon-channel entry gate
# ---------------------------------------------------------------------------

def test_dungeon_intimacy_clock_found_from_repo(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=3, segments=6)

    clock = coord.dungeon_intimacy_clock()

    assert clock is not None
    assert clock.category == "dungeon_intimacy"
    assert clock.filled == 3 and clock.segments == 6
    assert clock.monotonic is False


def test_dungeon_intimacy_clock_none_when_absent(tmp_path):
    coord, *_ = _make(tmp_path)
    assert coord.dungeon_intimacy_clock() is None


def test_begin_dungeon_dialogue_opens_when_gated_available(tmp_path):
    coord, chat, repo, *_ = _make(tmp_path, room_context={"resonance_point": True})
    _seed_intimacy_clock(repo, filled=4, segments=6)  # 0.66 ≥ 0.5

    coord.begin_dungeon_dialogue()

    assert coord.session is not None
    assert coord.session.kind == "dungeon"
    assert coord.session.room_id == "r1"
    assert chat.dialogue_mode is True


def test_begin_dungeon_dialogue_blocked_posts_lock_reason(tmp_path):
    from dungeon_daddy.rpg.dungeon_channel import REASON_NOT_HERE

    coord, chat, repo, *_ = _make(tmp_path, room_context={"resonance_point": False})
    _seed_intimacy_clock(repo, filled=1, segments=4)

    coord.begin_dungeon_dialogue()

    assert coord.session is None
    assert chat.dialogue_mode is None
    assert ("system", REASON_NOT_HERE) in chat.messages


# ---------------------------------------------------------------------------
# agent_inputs §4.4 context assembly
# ---------------------------------------------------------------------------

def test_agent_inputs_apply_knowledge_band_and_message(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    coord.dungeon_voice = "cold, industrial, analytical"
    coord.dungeon_knowledge = ["the heart still beats", "the warden lied", "a way down"]
    _seed_intimacy_clock(repo, filled=6, segments=6)  # full → all knowledge

    inputs = coord.agent_inputs("who built you?")

    assert inputs["dungeon_voice"] == "cold, industrial, analytical"
    assert inputs["intimacy_filled"] == 6 and inputs["intimacy_segments"] == 6
    assert inputs["dungeon_knowledge"] == [
        "the heart still beats", "the warden lied", "a way down",
    ]
    assert inputs["player_message"] == "who built you?"
    assert inputs["actor"] == "elara"


def test_agent_inputs_filters_knowledge_below_high_band(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    coord.dungeon_voice = "cryptic"
    coord.dungeon_knowledge = ["a", "b", "c", "d"]
    _seed_intimacy_clock(repo, filled=3, segments=6)  # 0.5 → cryptic head slice

    inputs = coord.agent_inputs("hello?")

    assert inputs["dungeon_knowledge"] == ["a", "b"]


def test_agent_inputs_carries_actor_identity(tmp_path):
    actor = _actor(display_name="Kira Vale", playbook_slug="artificer",
                   tags=["machine-touched", "exiled"])
    coord, _chat, repo, *_ = _make(tmp_path, actor=actor)
    _seed_intimacy_clock(repo, filled=6, segments=6)

    inputs = coord.agent_inputs("what am I to you?")

    assert inputs["actor_name"] == "Kira Vale"
    assert inputs["actor_playbook"]  # playbook display name resolved
    assert inputs["actor_tags"] == ["machine-touched", "exiled"]


def test_agent_inputs_carries_systems_status_without_dungeon(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=6, segments=6)
    _save_subsystem(repo, slug="coolant", name="Coolant Loop",
                    archetype="mechanism", state="damaged")
    _save_subsystem(repo, slug="altar", name="Altar",
                    archetype="container", state="closed")  # not a subsystem

    inputs = coord.agent_inputs("status report")

    assert inputs["systems_status"] == [("Coolant Loop", "damaged", "")]


def test_agent_inputs_systems_status_carries_location(tmp_path):
    coord, _chat, repo, *_ = _make(
        tmp_path, dungeon=_dungeon_model({"r1": (2, "Central Hub")})
    )
    _seed_intimacy_clock(repo, filled=6, segments=6)
    _save_subsystem(repo, slug="coolant", name="Coolant Loop",
                    archetype="mechanism", state="damaged")

    inputs = coord.agent_inputs("status report")

    assert inputs["systems_status"] == [("Coolant Loop", "damaged", "Level 2 — Central Hub")]


def test_agent_inputs_carries_next_objective_location(tmp_path):
    coord, _chat, repo, *_ = _make(
        tmp_path, dungeon=_dungeon_model({"r1": (2, "Central Hub")})
    )
    _seed_intimacy_clock(repo, filled=6, segments=6)
    _save_subsystem(repo, slug="coolant", name="Coolant Loop",
                    archetype="mechanism", state="damaged")
    _save_objective(repo, slug="tier0", tier=0, status="active",
                    description="Restore the coolant loop.")
    repo._conn.execute(
        "UPDATE objectives SET completion_target_slug = 'coolant' WHERE slug = 'tier0'"
    )

    inputs = coord.agent_inputs("where do you want me?")

    assert inputs["next_objective_location"] == "Level 2 — Central Hub"


def test_agent_inputs_objective_location_none_when_no_active(tmp_path):
    coord, _chat, repo, *_ = _make(
        tmp_path, dungeon=_dungeon_model({"r1": (2, "Central Hub")})
    )
    _seed_intimacy_clock(repo, filled=6, segments=6)

    inputs = coord.agent_inputs("where do you want me?")

    assert inputs["next_objective_location"] is None


def test_agent_inputs_carries_next_objective(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=6, segments=6)
    _save_objective(repo, slug="tier0", tier=0, status="completed")
    _save_objective(repo, slug="tier1", tier=1, status="active",
                    description="Restore the coolant loop and I shall trust you.")

    inputs = coord.agent_inputs("what do you want?")

    assert inputs["next_objective"] == "Restore the coolant loop and I shall trust you."


def test_agent_inputs_next_objective_none_when_no_active(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=6, segments=6)

    inputs = coord.agent_inputs("what do you want?")

    assert inputs["next_objective"] is None


def test_agent_inputs_carries_session_turns(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=6, segments=6)
    coord.session = DialogueSession(kind="dungeon", room_id="r1")
    coord.session.turns.append(("player", "Who built you?"))
    coord.session.turns.append(("dungeon", "Hands long since rusted."))

    inputs = coord.agent_inputs("and where are they now?")

    assert inputs["session_turns"] == [
        ("player", "Who built you?"),
        ("dungeon", "Hands long since rusted."),
    ]


def test_agent_inputs_session_turns_empty_without_session(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=6, segments=6)
    coord.session = None

    inputs = coord.agent_inputs("hello?")

    assert inputs["session_turns"] == []


def test_agent_inputs_knowledge_from_completed_tiers(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    coord.dungeon_knowledge = ["a flat back-compat secret"]
    _seed_intimacy_clock(repo, filled=1, segments=3)
    _save_objective(repo, slug="tier0", tier=0, status="completed",
                    knowledge=["the core is dying", "the warden is a copy"])
    _save_objective(repo, slug="tier1", tier=1, status="active",
                    knowledge=["a way down"])  # active tier stays gated

    inputs = coord.agent_inputs("what do you know?")

    assert inputs["dungeon_knowledge"] == ["the core is dying", "the warden is a copy"]


def test_agent_inputs_knowledge_falls_back_to_flat_when_no_objectives(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    coord.dungeon_knowledge = ["the heart still beats", "the warden lied", "a way down"]
    _seed_intimacy_clock(repo, filled=6, segments=6)

    inputs = coord.agent_inputs("who built you?")

    assert inputs["dungeon_knowledge"] == [
        "the heart still beats", "the warden lied", "a way down",
    ]


# ---------------------------------------------------------------------------
# persona attach
# ---------------------------------------------------------------------------

def test_set_persona_feeds_agent_inputs(tmp_path):
    coord, _chat, repo, *_ = _make(tmp_path)
    _seed_intimacy_clock(repo, filled=6, segments=6)

    coord.set_persona("cold, ancient, watchful", ["the heart still beats"])

    inputs = coord.agent_inputs("who built you?")
    assert inputs["dungeon_voice"] == "cold, ancient, watchful"
    assert inputs["dungeon_knowledge"] == ["the heart still beats"]


def test_set_persona_defaults_clear_attrs(tmp_path):
    coord, *_ = _make(tmp_path)
    coord.dungeon_voice = "stale"
    coord.dungeon_knowledge = ["stale secret"]

    coord.set_persona(None, [])

    assert coord.dungeon_voice is None
    assert coord.dungeon_knowledge == []


# ---------------------------------------------------------------------------
# dungeon send pipeline + reply application
# ---------------------------------------------------------------------------

def test_send_dungeon_line_threads_agent_and_builds_reply(tmp_path):
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _FakeProvider(reply="You return. Good.")
    coord, chat, repo, _session, narr = _make(
        tmp_path, voice_agent=DungeonVoiceAgent(provider)
    )
    coord.session = DialogueSession(kind="dungeon", room_id="r1")
    coord.dungeon_voice = "cold"
    _seed_intimacy_clock(repo, filled=4, segments=6)

    coord.send_dungeon_line("I'm back")

    # The player's line is echoed and recorded immediately (synchronous).
    assert ("gm", "I'm back") in chat.messages
    assert ("player", "I'm back") in coord.session.turns
    assert chat.busy is True
    # The worker was handed to narration; running it produces the dungeon result.
    result = narr.worker()
    assert isinstance(result, DMResult)
    assert result.dungeon is True
    assert result.content == "You return. Good."
    assert result.player_message == "I'm back"
    assert len(provider.calls) == 1


def test_send_dungeon_line_silent_without_agent(tmp_path):
    coord, chat, repo, _session, narr = _make(tmp_path, voice_agent=None)
    coord.session = DialogueSession(kind="dungeon", room_id="r1")

    coord.send_dungeon_line("anyone there?")

    assert ("system", "The dungeon is silent. (voice agent unavailable)") in chat.messages
    assert narr.worker is None  # nothing spawned


def test_send_dungeon_line_noop_when_busy(tmp_path):
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent

    provider = _FakeProvider()
    coord, chat, repo, _session, narr = _make(
        tmp_path, voice_agent=DungeonVoiceAgent(provider),
        narration=_FakeNarration(busy=True),
    )
    coord.session = DialogueSession(kind="dungeon", room_id="r1")

    coord.send_dungeon_line("busy?")

    # The line is still echoed, but no worker is spawned and no busy spinner set.
    assert ("gm", "busy?") in chat.messages
    assert narr.worker is None
    assert chat.busy is None


def test_apply_dungeon_reply_posts_bubble_and_records_exchange(tmp_path):
    coord, chat, repo, _session, _ = _make(tmp_path)
    coord.session = DialogueSession(kind="dungeon", room_id="r1")
    _seed_intimacy_clock(repo, filled=3, segments=6)

    coord.apply_dungeon_reply("who are you?", "I am the deep.")

    assert ("dungeon", "I am the deep.") in chat.messages
    # Phase 51.5 (D1/D5): chat no longer ticks intimacy.
    clock = coord.dungeon_intimacy_clock()
    assert clock.filled == 3
    # An approved memory of the exchange is written engine-side.
    assert repo.count_by_status("camp-1") == {"approved": 1}
    assert ("dungeon", "I am the deep.") in coord.session.turns
