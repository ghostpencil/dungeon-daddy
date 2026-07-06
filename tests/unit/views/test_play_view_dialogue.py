"""Phase 51 Slice 8 — PlayView dialogue routing (DialogueSession).

Replaces the 50.6 dialogue stub with real routing: an in-memory ``DialogueSession``
dispatched by ``kind`` ("dungeon" / "npc"). These tests exercise the routing and
engine side-effects through the public PlayView callbacks, using a real
MemoryRepository and a fake LLM provider (no network).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
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


def _make_view(tmp_path: Path, actor: ActorState | None = None):
    from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel
    from dungeon_daddy.ui.player_action_state import PlayerActionState
    from dungeon_daddy.views.play_view import PlayView

    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    actor = actor or _actor()
    view = PlayView.__new__(PlayView)
    view._mem_repo = mem_repo
    view._rpg_campaign_id = "camp-1"
    view._state = SessionState(
        dungeon_id="d1", current_level_idx=0,
        current_room_id="r1", visited_rooms=["r1"],
    )
    view._dungeon = None
    view._rpg_vna = VnaActionPanel()
    view._rpg_action = MagicMock()
    view._session.set_actors([actor])
    view._action_state = PlayerActionState()
    view._action_state.set_actor_roster([actor.actor_id])
    view._chat = MagicMock()
    view._dialogue = None
    return view


# ---------------------------------------------------------------------------
# Cycle 1 — _on_chat_send routes to dialogue while a session is active
# ---------------------------------------------------------------------------

def test_chat_send_routes_to_dialogue_when_session_active(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._on_dialogue_send = MagicMock()
    view._dialogue = DialogueSession(kind="npc", room_id="r1", target_id="npc-1")

    view._on_chat_send("hello warden")

    view._on_dialogue_send.assert_called_once_with("hello warden")


# ---------------------------------------------------------------------------
# Cycle 2 — NPC dialogue via the shared engine + /leave close
# ---------------------------------------------------------------------------

def test_begin_dialogue_opens_npc_session(tmp_path):
    view = _make_view(tmp_path)

    view._begin_dialogue(kind="npc", room_id="r1", target_id="npc-1",
                         opener="You open a conversation with the Warden.")

    assert view._dialogue is not None
    assert view._dialogue.kind == "npc"
    assert view._dialogue.target_id == "npc-1"
    assert view._dialogue.room_id == "r1"
    view._chat.set_dialogue_mode.assert_called_once_with(True)


def test_leave_command_closes_dialogue(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._dialogue = DialogueSession(kind="npc", room_id="r1", target_id="npc-1")

    view._on_dialogue_send("/leave")

    assert view._dialogue is None
    view._chat.set_dialogue_mode.assert_called_once_with(False)


def test_npc_line_records_turn_and_stays_open(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._dialogue = DialogueSession(kind="npc", room_id="r1", target_id="npc-1")

    view._on_dialogue_send("well met")

    # A thin binding (D1a): the line is posted and the channel stays open until
    # /leave or a room change — it does not end the conversation immediately.
    assert view._dialogue is not None
    assert ("player", "well met") in view._dialogue.turns
    view._chat.set_dialogue_mode.assert_not_called()


# ---------------------------------------------------------------------------
# Cycle 3 — dungeon channel entry + intimacy clock lookup
# ---------------------------------------------------------------------------

def _seed_intimacy_clock(repo, *, filled, segments, campaign_id="camp-1"):
    repo.save_clock(
        clock_id="intimacy-1", campaign_id=campaign_id,
        label="Dungeon Intimacy", segments=segments, filled=filled,
        clock_level="dungeon", category="dungeon_intimacy", monotonic=False,
    )


def test_dungeon_intimacy_clock_found_from_repo(tmp_path):
    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=3, segments=6)

    clock = view._dungeon_intimacy_clock()

    assert clock is not None
    assert clock.category == "dungeon_intimacy"
    assert clock.filled == 3 and clock.segments == 6
    assert clock.monotonic is False


def test_dungeon_intimacy_clock_none_when_absent(tmp_path):
    view = _make_view(tmp_path)
    assert view._dungeon_intimacy_clock() is None


def test_begin_dungeon_dialogue_opens_when_gated_available(tmp_path):
    view = _make_view(tmp_path)
    view._last_room_context = {"resonance_point": True}
    _seed_intimacy_clock(view._mem_repo, filled=4, segments=6)  # 0.66 ≥ 0.5

    view._begin_dungeon_dialogue()

    assert view._dialogue is not None
    assert view._dialogue.kind == "dungeon"
    assert view._dialogue.room_id == "r1"
    view._chat.set_dialogue_mode.assert_called_once_with(True)


def test_begin_dungeon_dialogue_blocked_posts_lock_reason(tmp_path):
    # Phase 51.5 D6: low intimacy no longer closes the channel (it opens cryptic
    # at tier 0); the still-closed case is standing off a resonance point.
    from dungeon_daddy.rpg.dungeon_channel import REASON_NOT_HERE

    view = _make_view(tmp_path)
    view._last_room_context = {"resonance_point": False}
    _seed_intimacy_clock(view._mem_repo, filled=1, segments=4)

    view._begin_dungeon_dialogue()

    assert view._dialogue is None
    view._chat.set_dialogue_mode.assert_not_called()
    view._chat.add_message.assert_called_once_with("system", REASON_NOT_HERE)


# ---------------------------------------------------------------------------
# Cycle 4 — dungeon send pipeline (agent inputs + engine side-effects)
# ---------------------------------------------------------------------------

class _FakeProvider:
    """Records the last call and returns a canned reply (no network)."""

    def __init__(self, reply="I have watched you a long time."):
        self.reply = reply
        self.calls: list[dict] = []

    def complete(self, *, messages, system, max_tokens):
        self.calls.append({"messages": messages, "system": system})
        return self.reply


def test_dungeon_agent_inputs_apply_knowledge_band_and_message(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon_voice = "cold, industrial, analytical"
    view._dungeon_knowledge = ["the heart still beats", "the warden lied", "a way down"]
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)  # full → all knowledge

    inputs = view._dungeon_agent_inputs("who built you?")

    assert inputs["dungeon_voice"] == "cold, industrial, analytical"
    assert inputs["intimacy_filled"] == 6 and inputs["intimacy_segments"] == 6
    assert inputs["dungeon_knowledge"] == [
        "the heart still beats", "the warden lied", "a way down",
    ]
    assert inputs["player_message"] == "who built you?"
    assert inputs["actor"] == "elara"


def test_dungeon_agent_inputs_filters_knowledge_below_high_band(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon_voice = "cryptic"
    view._dungeon_knowledge = ["a", "b", "c", "d"]
    _seed_intimacy_clock(view._mem_repo, filled=3, segments=6)  # 0.5 → cryptic head slice

    inputs = view._dungeon_agent_inputs("hello?")

    # Cryptic band reveals only a fragmentary head slice (ceil(4 * 0.5) = 2).
    assert inputs["dungeon_knowledge"] == ["a", "b"]


# ---------------------------------------------------------------------------
# P4 — set_dungeon_persona feeds the agent inputs end-to-end
# ---------------------------------------------------------------------------

def test_set_dungeon_persona_feeds_agent_inputs(tmp_path):
    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)  # full → all knowledge

    view.set_dungeon_persona("cold, ancient, watchful", ["the heart still beats"])

    inputs = view._dungeon_agent_inputs("who built you?")
    assert inputs["dungeon_voice"] == "cold, ancient, watchful"
    assert inputs["dungeon_knowledge"] == ["the heart still beats"]


def test_set_dungeon_persona_defaults_clear_attrs(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon_voice = "stale"
    view._dungeon_knowledge = ["stale secret"]

    view.set_dungeon_persona(None, [])

    assert view._dungeon_voice is None
    assert view._dungeon_knowledge == []


def test_apply_dungeon_reply_posts_bubble_and_records_exchange(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._dialogue = DialogueSession(kind="dungeon", room_id="r1")
    _seed_intimacy_clock(view._mem_repo, filled=3, segments=6)

    view._apply_dungeon_reply("who are you?", "I am the deep.")

    # The reply lands in the dedicated dungeon-voice bubble (§4.6) — a distinct
    # role from ordinary DM narration ("dm").
    view._chat.add_message.assert_any_call("dungeon", "I am the deep.")
    # Phase 51.5 (D1/D5): chat no longer ticks intimacy — the clock is left
    # untouched; the objective service is now the single intimacy-tick source.
    clock = view._dungeon_intimacy_clock()
    assert clock.filled == 3
    # An approved memory of the exchange is written (owner override 2026-06-28):
    # engine-authored, no curation queue, feeds back via MemoryRetriever.
    assert view._mem_repo.count_by_status("camp-1") == {"approved": 1}
    # The dungeon turn is recorded on the session.
    assert ("dungeon", "I am the deep.") in view._dialogue.turns


def test_send_dungeon_line_threads_agent_and_queues_reply(tmp_path):
    import queue as _queue

    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._dialogue = DialogueSession(kind="dungeon", room_id="r1")
    view._dungeon_voice = "cold"
    view._dungeon_knowledge = []
    _seed_intimacy_clock(view._mem_repo, filled=4, segments=6)
    view._result_queue = _queue.Queue()
    view._llm_busy = False
    provider = _FakeProvider(reply="You return. Good.")
    view._dungeon_voice_agent = DungeonVoiceAgent(provider)

    view._send_dungeon_line("I'm back")

    # The player's line is echoed and recorded immediately (synchronous).
    view._chat.add_message.assert_any_call("gm", "I'm back")
    assert ("player", "I'm back") in view._dialogue.turns
    # The agent call runs off-thread and queues a dungeon-marked reply.
    view._active_thread.join(timeout=5)
    result = view._result_queue.get_nowait()
    assert result.dungeon is True
    assert result.content == "You return. Good."
    assert result.player_message == "I'm back"
    assert len(provider.calls) == 1


def test_on_update_routes_dungeon_result_to_apply(tmp_path):
    import queue as _queue

    from dungeon_daddy.views.play_view import DMResult

    view = _make_view(tmp_path)
    view._apply_dungeon_reply = MagicMock()
    view._result_queue = _queue.Queue()
    view._llm_busy = True
    view._result_queue.put(
        DMResult(content="I remember.", dungeon=True, player_message="do you recall?")
    )

    view.on_update(0.0)

    view._apply_dungeon_reply.assert_called_once_with("do you recall?", "I remember.")


# ---------------------------------------------------------------------------
# Cycle 5 — leaving the room closes an open dialogue (spec §4.3)
# ---------------------------------------------------------------------------

def test_room_change_closes_open_dialogue(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._dialogue = DialogueSession(kind="dungeon", room_id="r1")
    view._state.current_room_id = "r2"  # the party has left the resonance room

    view._maybe_end_dialogue_on_room_change()

    assert view._dialogue is None
    view._chat.set_dialogue_mode.assert_called_once_with(False)


def test_dialogue_stays_open_in_same_room(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    view._dialogue = DialogueSession(kind="dungeon", room_id="r1")
    # still standing in r1

    view._maybe_end_dialogue_on_room_change()

    assert view._dialogue is not None
    view._chat.set_dialogue_mode.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 51.5 Slice 8 — _dungeon_agent_inputs assembles the §4.4 context
# ---------------------------------------------------------------------------

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


def test_dungeon_agent_inputs_carries_actor_identity(tmp_path):
    actor = _actor(display_name="Kira Vale", playbook_slug="artificer",
                   tags=["machine-touched", "exiled"])
    view = _make_view(tmp_path, actor=actor)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)

    inputs = view._dungeon_agent_inputs("what am I to you?")

    assert inputs["actor_name"] == "Kira Vale"
    assert inputs["actor_playbook"]  # playbook display name resolved
    assert inputs["actor_tags"] == ["machine-touched", "exiled"]


def _dungeon_model(room_labels):
    """Minimal dungeon model (levels→rooms) for room-label resolution.

    ``room_labels`` maps room_id -> (level_id, room_name).
    """
    from types import SimpleNamespace

    by_level: dict = {}
    for room_id, (level_id, room_name) in room_labels.items():
        by_level.setdefault(level_id, []).append(
            SimpleNamespace(id=room_id, name=room_name)
        )
    levels = [SimpleNamespace(id=lid, rooms=rooms) for lid, rooms in by_level.items()]
    return SimpleNamespace(levels=levels)


def test_dungeon_agent_inputs_carries_systems_status(tmp_path):
    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)
    _save_subsystem(view._mem_repo, slug="coolant", name="Coolant Loop",
                    archetype="mechanism", state="damaged")
    _save_subsystem(view._mem_repo, slug="altar", name="Altar",
                    archetype="container", state="closed")  # not a subsystem

    inputs = view._dungeon_agent_inputs("status report")

    # No dungeon model loaded → location is blank but state is still reported.
    assert inputs["systems_status"] == [("Coolant Loop", "damaged", "")]


def test_dungeon_agent_inputs_systems_status_carries_location(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon = _dungeon_model({"r1": (2, "Central Hub")})
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)
    _save_subsystem(view._mem_repo, slug="coolant", name="Coolant Loop",
                    archetype="mechanism", state="damaged")

    inputs = view._dungeon_agent_inputs("status report")

    assert inputs["systems_status"] == [("Coolant Loop", "damaged", "Level 2 — Central Hub")]


def test_dungeon_agent_inputs_carries_next_objective_location(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon = _dungeon_model({"r1": (2, "Central Hub")})
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)
    # The objective's target object lives in r1 (the subsystem saved below).
    _save_subsystem(view._mem_repo, slug="coolant", name="Coolant Loop",
                    archetype="mechanism", state="damaged")
    _save_objective(view._mem_repo, slug="tier0", tier=0, status="active",
                    description="Restore the coolant loop.")
    # point the active objective at the coolant subsystem
    view._mem_repo._conn.execute(
        "UPDATE objectives SET completion_target_slug = 'coolant' WHERE slug = 'tier0'"
    )

    inputs = view._dungeon_agent_inputs("where do you want me?")

    assert inputs["next_objective_location"] == "Level 2 — Central Hub"


def test_dungeon_agent_inputs_objective_location_none_when_no_active(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon = _dungeon_model({"r1": (2, "Central Hub")})
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)

    inputs = view._dungeon_agent_inputs("where do you want me?")

    assert inputs["next_objective_location"] is None


def test_dungeon_agent_inputs_carries_next_objective(tmp_path):
    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)
    _save_objective(view._mem_repo, slug="tier0", tier=0, status="completed")
    _save_objective(view._mem_repo, slug="tier1", tier=1, status="active",
                    description="Restore the coolant loop and I shall trust you.")

    inputs = view._dungeon_agent_inputs("what do you want?")

    assert inputs["next_objective"] == "Restore the coolant loop and I shall trust you."


def test_dungeon_agent_inputs_next_objective_none_when_no_active(tmp_path):
    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)

    inputs = view._dungeon_agent_inputs("what do you want?")

    assert inputs["next_objective"] is None


def test_dungeon_agent_inputs_carries_session_turns(tmp_path):
    from dungeon_daddy.views.play_view import DialogueSession

    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)
    view._dialogue = DialogueSession(kind="dungeon", room_id="r1")
    view._dialogue.turns.append(("player", "Who built you?"))
    view._dialogue.turns.append(("dungeon", "Hands long since rusted."))

    inputs = view._dungeon_agent_inputs("and where are they now?")

    assert inputs["session_turns"] == [
        ("player", "Who built you?"),
        ("dungeon", "Hands long since rusted."),
    ]


def test_dungeon_agent_inputs_session_turns_empty_without_session(tmp_path):
    view = _make_view(tmp_path)
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)
    view._dialogue = None

    inputs = view._dungeon_agent_inputs("hello?")

    assert inputs["session_turns"] == []


def test_dungeon_agent_inputs_knowledge_from_completed_tiers(tmp_path):
    # D7: tier knowledge (union over completed objectives) replaces the flat
    # reveal_knowledge band when objectives exist.
    view = _make_view(tmp_path)
    view._dungeon_knowledge = ["a flat back-compat secret"]
    _seed_intimacy_clock(view._mem_repo, filled=1, segments=3)
    _save_objective(view._mem_repo, slug="tier0", tier=0, status="completed",
                    knowledge=["the core is dying", "the warden is a copy"])
    _save_objective(view._mem_repo, slug="tier1", tier=1, status="active",
                    knowledge=["a way down"])  # active tier stays gated

    inputs = view._dungeon_agent_inputs("what do you know?")

    assert inputs["dungeon_knowledge"] == ["the core is dying", "the warden is a copy"]


def test_dungeon_agent_inputs_knowledge_falls_back_to_flat_when_no_objectives(tmp_path):
    # Back-compat: with no objectives authored, the old reveal_knowledge band path
    # still drives dungeon_knowledge.
    view = _make_view(tmp_path)
    view._dungeon_knowledge = ["the heart still beats", "the warden lied", "a way down"]
    _seed_intimacy_clock(view._mem_repo, filled=6, segments=6)  # full → all flat knowledge

    inputs = view._dungeon_agent_inputs("who built you?")

    assert inputs["dungeon_knowledge"] == [
        "the heart still beats", "the warden lied", "a way down",
    ]
