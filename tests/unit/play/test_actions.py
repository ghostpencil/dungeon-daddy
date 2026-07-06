"""Phase 51.7 Slice 4 — ActionOrchestrator (play/actions.py).

Unit tests for the action seam extracted from ``PlayView``: the ``on_vna_submit``
dispatch tree (look/activate/use branches), the card roll path, command
application + objective advancement, the obstacle seams, and the proposal
pipeline. The orchestrator imports no ``arcade`` — it is exercised directly
against a real ``MemoryRepository`` + ``PlaySessionContext`` and recording ports
(no PlayView, no window).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.actions import ActionOrchestrator, describe_spawned_loot
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


class _Ports:
    """Records every side-effect port call the orchestrator makes."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.narration_requests: list[str] = []
        self.vna_refreshes: int = 0
        self.right_panel_refreshes: list[str] = []
        self.exit_moves: list[tuple[str, str, str | None]] = []
        self.begin_dialogue_calls: list[dict[str, Any]] = []
        self.cleared_locks: list[tuple[str, str]] = []
        self.stored_results: list[dict[str, Any]] = []

    def post(self, role: str, text: str) -> None:
        self.messages.append((role, text))


class _FakeNarration:
    """Minimal stand-in for NarrationCoordinator: records narration requests."""

    def __init__(self, ports: _Ports) -> None:
        self._ports = ports

    def request_narration(self, msg: str) -> None:
        self._ports.narration_requests.append(msg)


def _dungeon():
    """One-level dungeon whose single room id matches the session's ``r1``."""
    from dungeon_daddy.data.models import (
        Connection,
        Dungeon,
        DungeonMeta,
        Level,
        Room,
    )

    rooms = [Room(id="r1", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")]
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="lock_key",
        width=12, height=10, entries=[], rooms=rooms,
        connections=[Connection(from_room="r1", to_room="r1", type="door")],
    )
    return Dungeon(
        meta=DungeonMeta(title="T", theme="", setting="", party="", quest=""),
        levels=[level],
    )


def _make(
    tmp_path: Path,
    *,
    actor: ActorState | None = None,
    dungeon: Any = None,
    rpg_service: Any = None,
    dm_agent: Any = None,
    debug: Any = None,
    nouns: list[Any] | None = None,
    room_context: dict[str, Any] | None = None,
    acting_actor: ActorState | None = None,
) -> tuple[ActionOrchestrator, _Ports, MemoryRepository, PlaySessionContext]:
    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    the_actor = actor or _actor()
    session = PlaySessionContext(
        dungeon=dungeon,
        state=SessionState(
            dungeon_id="d1", current_level_idx=0,
            current_room_id="r1", visited_rooms=["r1"],
        ),
        mem_repo=mem_repo,
        campaign_id="camp-1",
        actors=[the_actor],
    )
    ports = _Ports()
    narration = _FakeNarration(ports)
    orchestrator = ActionOrchestrator(
        session,
        get_rpg_service=lambda: rpg_service,
        get_dm_agent=lambda: dm_agent,
        get_debug=lambda: debug,
        get_narration=lambda: narration,
        get_acting_actor=lambda: acting_actor or session.acting_actor(),
        get_nouns=lambda: nouns or [],
        get_room_context=lambda: room_context or {},
        post_message=ports.post,
        begin_dialogue=lambda **kw: ports.begin_dialogue_calls.append(kw),
        on_exit_move=lambda exit_id, how, item_slug=None: ports.exit_moves.append(
            (exit_id, how, item_slug)
        ),
        clear_connection_lock=lambda f, t: ports.cleared_locks.append((f, t)),
        refresh_vna_panel=lambda: setattr(
            ports, "vna_refreshes", ports.vna_refreshes + 1
        ),
        refresh_right_panel=ports.right_panel_refreshes.append,
        build_request=_build_request,
        format_result=_format_result,
        store_result=ports.stored_results.append,
    )
    return orchestrator, ports, mem_repo, session


def _build_request(**kw: Any) -> Any:
    """The PlayerActionPanel._build_request seam — a real ActionRequest."""
    from dungeon_daddy.rpg.models import ActionRequest

    return ActionRequest(**kw)


def _format_result(resolution: Any) -> dict[str, Any]:
    """The PlayerActionPanel._format_result seam — same dict shape."""
    return {
        "outcome": resolution.outcome,
        "dice": resolution.dice_rolled,
        "stress_cost": resolution.stress_cost,
        "notes": resolution.notes,
    }


def _save_subsystem(repo, *, slug, name, archetype, state, campaign_id="camp-1"):
    from dungeon_daddy.rpg.models import RoomObject

    repo.save_room_object(
        RoomObject(
            object_id=f"obj-{slug}", campaign_id=campaign_id, room_id="r1",
            level_id="l1", slug=slug, display_name=name, archetype=archetype,
            description="A dungeon subsystem.", current_state=state,
        )
    )


def _save_objective(repo, *, slug, tier, status, target_slug="x",
                    required_state="restored", campaign_id="camp-1"):
    from dungeon_daddy.rpg.models import Objective, ObjectiveCompletion

    repo.save_objective(
        Objective(
            objective_id=f"obj:{slug}", campaign_id=campaign_id, slug=slug,
            title=slug.replace("-", " ").title(), description="Restore it.",
            tier_index=tier, status=status,
            completion=ObjectiveCompletion(
                kind="object_state", target_slug=target_slug,
                required_state=required_state,
            ),
            advances_clock_slug="dungeon_intimacy",
        )
    )


def _seed_intimacy_clock(repo, *, filled=0, segments=4, campaign_id="camp-1"):
    repo.save_clock(
        clock_id="intimacy-1", campaign_id=campaign_id,
        label="Dungeon Intimacy", segments=segments, filled=filled,
        clock_level="dungeon", category="dungeon_intimacy", monotonic=False,
    )


# ---------------------------------------------------------------------------
# apply_vna_command — validate + apply a non-move mutation command
# ---------------------------------------------------------------------------


def test_apply_vna_command_rejected_posts_warning_and_returns_false(tmp_path):
    from dungeon_daddy.rpg.command import ActivateObject

    orchestrator, ports, _repo, _ = _make(tmp_path)

    accepted = orchestrator.apply_vna_command(
        ActivateObject(actor_id="pc-1", object_id="no-such-object", trigger="pull")
    )

    assert accepted is False
    assert len(ports.messages) == 1
    role, text = ports.messages[0]
    assert role == "system"
    assert text.startswith("⚠ Can't do that:")
    assert ports.vna_refreshes == 0


def _save_object_with_transition(
    repo, *, slug="lever", state="ready", to_state="pulled", trigger="pull",
    contested=False, action_verb=None, campaign_id="camp-1",
):
    from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

    obj = RoomObject(
        object_id=f"obj-{slug}", campaign_id=campaign_id, room_id="r1",
        level_id="l1", slug=slug, display_name=slug.title(), archetype="mechanism",
        description="A heavy brass lever.", current_state=state,
        transitions=[
            ObjectTransition(
                transition_id=f"t-{slug}", object_id=f"obj-{slug}",
                from_state=state, to_state=to_state, trigger=trigger,
                contested=contested, action_verb=action_verb,
            )
        ],
    )
    repo.save_room_object(obj)
    return obj


def test_apply_vna_command_accepted_applies_advances_and_refreshes(tmp_path):
    from dungeon_daddy.rpg.command import ActivateObject

    orchestrator, ports, repo, _ = _make(tmp_path)
    _save_object_with_transition(repo, slug="lever", state="ready")
    _seed_intimacy_clock(repo)
    _save_objective(
        repo, slug="pull-the-lever", tier=0, status="active",
        target_slug="lever", required_state="pulled",
    )

    accepted = orchestrator.apply_vna_command(
        ActivateObject(actor_id="pc-1", object_id="obj-lever", trigger="pull")
    )

    assert accepted is True
    assert repo.get_room_object("obj-lever")["current_state"] == "pulled"
    # The mutation re-advanced objectives (the satisfied tier posts its line).
    assert ("dungeon", "◆ The Crucible stirs — its bond with you deepens.") in ports.messages
    assert ports.vna_refreshes == 1


# ---------------------------------------------------------------------------
# look — read-only description fetch (no dice, no state change)
# ---------------------------------------------------------------------------


def _noun(noun_id, label, *, target_type="object", slug=None, source="object"):
    from dungeon_daddy.rpg.action_options import NounOption

    return NounOption(
        noun_id=noun_id, label=label, target_type=target_type,
        slug=slug, source=source,
    )


def test_on_look_submit_posts_the_authoritative_description(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, _ = _make(
        tmp_path, nouns=[_noun("obj-lever", "Brass Lever")],
    )
    _save_object_with_transition(repo, slug="lever", state="ready")

    orchestrator.on_look_submit(
        ActionCard(verb="look", noun_id="obj-lever", adverb="carefully")
    )

    assert ports.messages == [("system", "Brass Lever: A heavy brass lever.")]


def test_on_look_submit_warns_when_nothing_to_read(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, _repo, _ = _make(tmp_path)

    orchestrator.on_look_submit(
        ActionCard(verb="look", noun_id="ghost", adverb="carefully")
    )

    assert ports.messages == [("system", "⚠ Nothing to read about ghost.")]


# ---------------------------------------------------------------------------
# activate — trigger selection, deterministic vs contested routing
# ---------------------------------------------------------------------------


def test_on_activate_submit_deterministic_applies_posts_and_narrates(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, session = _make(tmp_path, dungeon=_dungeon())
    _save_object_with_transition(repo, slug="lever", state="ready")

    orchestrator.on_activate_submit(
        ActionCard(verb="activate", noun_id="obj-lever", adverb="carefully"),
        session.acting_actor(),
    )

    assert repo.get_room_object("obj-lever")["current_state"] == "pulled"
    assert ("system", "Lever: pulled.") in ports.messages
    assert ports.narration_requests == [
        "Elara pull the Lever. [Lever: ready → pulled]"
    ]


def test_on_activate_submit_warns_when_no_matching_transition(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, session = _make(tmp_path)
    # Object exists but its only transition starts from a different state.
    _save_object_with_transition(repo, slug="lever", state="ready")
    repo.update_object_state("obj-lever", "jammed")

    orchestrator.on_activate_submit(
        ActionCard(verb="activate", noun_id="obj-lever", adverb="carefully"),
        session.acting_actor(),
    )

    assert ports.messages == [
        ("system", "⚠ Nothing to do with this object right now.")
    ]


def test_on_activate_submit_warns_when_object_missing(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, _repo, session = _make(tmp_path)

    orchestrator.on_activate_submit(
        ActionCard(verb="activate", noun_id="ghost", adverb="carefully"),
        session.acting_actor(),
    )

    assert ports.messages == [("system", "⚠ Object not found: ghost")]


# ---------------------------------------------------------------------------
# resolve_vna_roll — skill-verb card → action roll → bubble + narration
# ---------------------------------------------------------------------------


def test_resolve_vna_roll_posts_bubble_narrates_noun_and_refreshes(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.service import RpgService

    orchestrator, ports, repo, session = _make(
        tmp_path,
        dungeon=_dungeon(),
        rpg_service=RpgService(),
        nouns=[_noun("obj-board", "Warden's Notice Board")],
    )
    _save_subsystem(
        repo, slug="board", name="Warden's Notice Board",
        archetype="lore_fixture", state="default",
    )

    orchestrator.resolve_vna_roll(
        ActionCard(verb="study", noun_id="obj-board", adverb="cautiously"),
        session.acting_actor(),
    )

    # Mechanical bubble posted (any dice outcome).
    assert any(
        role == "system" and "rolls" in text for role, text in ports.messages
    )
    # The DM narration names the acted-upon noun and the verb.
    assert len(ports.narration_requests) == 1
    assert "Warden's Notice Board" in ports.narration_requests[0]
    assert "[STUDY]" in ports.narration_requests[0]
    # Right panel synced to the acting actor.
    assert ports.right_panel_refreshes == ["pc-1"]


# ---------------------------------------------------------------------------
# maybe_resolve_obstacle — contested approaches (Phase 51.5 Part A)
# ---------------------------------------------------------------------------


def test_maybe_resolve_obstacle_full_success_applies_the_transition(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, _ports, repo, session = _make(tmp_path)
    _save_object_with_transition(
        repo, slug="gate", state="sealed", to_state="breached",
        trigger="force", contested=True, action_verb="fight",
    )

    resolved = orchestrator.maybe_resolve_obstacle(
        ActionCard(verb="fight", noun_id="obj-gate", adverb="boldly"),
        session.acting_actor(),
        "full",
    )

    assert resolved is not None
    assert resolved.transition.to_state == "breached"
    assert repo.get_room_object("obj-gate")["current_state"] == "breached"


def test_maybe_resolve_obstacle_miss_changes_nothing(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, _ports, repo, session = _make(tmp_path)
    _save_object_with_transition(
        repo, slug="gate", state="sealed", to_state="breached",
        trigger="force", contested=True, action_verb="fight",
    )

    resolved = orchestrator.maybe_resolve_obstacle(
        ActionCard(verb="fight", noun_id="obj-gate", adverb="boldly"),
        session.acting_actor(),
        "miss",
    )

    assert resolved is None
    assert repo.get_room_object("obj-gate")["current_state"] == "sealed"


# ---------------------------------------------------------------------------
# on_vna_submit — the dispatch tree
# ---------------------------------------------------------------------------


def test_on_vna_submit_sway_on_willing_creature_opens_dialogue_not_roll(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, _repo, _ = _make(
        tmp_path,
        nouns=[_noun("npc-1", "Mira", target_type="npc", source="npc")],
        room_context={"npcs": [{"actor_id": "npc-1", "disposition": "willing"}]},
    )

    orchestrator.on_vna_submit(
        ActionCard(verb="sway", noun_id="npc-1", adverb="cautiously")
    )

    assert ports.begin_dialogue_calls == [
        {
            "kind": "npc",
            "room_id": "r1",
            "target_id": "npc-1",
            "opener": "You open a conversation with Mira.",
        }
    ]
    # No roll happened — no mechanical bubble, no narration.
    assert ports.messages == []
    assert ports.narration_requests == []


def test_on_vna_submit_look_routes_to_the_read_only_branch(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, _ = _make(
        tmp_path, nouns=[_noun("obj-lever", "Brass Lever")],
    )
    _save_object_with_transition(repo, slug="lever", state="ready")

    orchestrator.on_vna_submit(
        ActionCard(verb="look", noun_id="obj-lever", adverb="carefully")
    )

    assert ports.messages == [("system", "Brass Lever: A heavy brass lever.")]
    # Read-only: no state change, no roll, no refresh.
    assert repo.get_room_object("obj-lever")["current_state"] == "ready"
    assert ports.narration_requests == []


def test_on_vna_submit_move_card_routes_to_exit_move(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, _repo, _ = _make(tmp_path)

    orchestrator.on_vna_submit(
        ActionCard(verb="move", noun_id="exit-1", adverb="cautiously")
    )

    assert ports.exit_moves == [("exit-1", "cautiously", None)]


def _save_locked_exit(repo, *, requires_item_slug):
    from dungeon_daddy.rpg.models import RoomExit

    repo.save_room_exit(RoomExit(
        exit_id="exit-1", campaign_id="camp-1", from_room_id="r1",
        to_room_id="r2", level_id="l1", label="Iron Door", status="locked",
        requires_item_slug=requires_item_slug,
    ))


def test_on_vna_submit_use_key_on_locked_exit_unlocks_it(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, _ = _make(
        tmp_path,
        nouns=[
            _noun("itm-key", "Brass Key", target_type="item",
                  slug="brass-key", source="carried_item"),
            _noun("exit-1", "🔒 Iron Door", target_type="room",
                  source="locked_exit"),
        ],
    )
    _save_locked_exit(repo, requires_item_slug="brass-key")

    orchestrator.on_vna_submit(
        ActionCard(verb="use", noun_id="itm-key", adverb="carefully",
                   target_id="exit-1")
    )

    assert repo.get_exit_by_id("exit-1")["requires_item_slug"] is None
    assert ports.cleared_locks == [("r1", "r2")]
    assert ("system", "Iron Door: unlocked.") in ports.messages
    assert ports.vna_refreshes == 1
    assert ports.exit_moves == []  # unlocking does not walk through


def test_on_vna_submit_use_nonkey_on_exit_attempts_the_move(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, _ = _make(
        tmp_path,
        nouns=[
            _noun("itm-rope", "Rope", target_type="item",
                  slug="rope", source="carried_item"),
            _noun("exit-1", "Iron Door", target_type="room", source="exit"),
        ],
    )
    _save_locked_exit(repo, requires_item_slug="brass-key")

    orchestrator.on_vna_submit(
        ActionCard(verb="use", noun_id="itm-rope", adverb="carefully",
                   target_id="exit-1")
    )

    assert ports.exit_moves == [("exit-1", "carefully", "rope")]
    assert ports.cleared_locks == []


def test_on_vna_submit_use_on_object_routes_to_activate(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    orchestrator, ports, repo, _ = _make(
        tmp_path,
        nouns=[
            _noun("itm-oil", "Oil Flask", target_type="item",
                  slug="oil-flask", source="carried_item"),
            _noun("obj-lever", "Lever", target_type="object", source="object"),
        ],
    )
    _save_object_with_transition(repo, slug="lever", state="ready")

    orchestrator.on_vna_submit(
        ActionCard(verb="use", noun_id="itm-oil", adverb="carefully",
                   target_id="obj-lever")
    )

    assert repo.get_room_object("obj-lever")["current_state"] == "pulled"
    assert ("system", "Lever: pulled.") in ports.messages


def test_on_vna_submit_skill_verb_falls_through_to_the_roll(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.service import RpgService

    orchestrator, ports, _repo, _ = _make(
        tmp_path, rpg_service=RpgService(),
        nouns=[_noun("obj-x", "Odd Machine")],
    )

    orchestrator.on_vna_submit(
        ActionCard(verb="study", noun_id="obj-x", adverb="cautiously")
    )

    assert any(
        role == "system" and "rolls" in text for role, text in ports.messages
    )


# ---------------------------------------------------------------------------
# run_chat_action / on_resolve_action — the chat-side roll paths (no noun)
# ---------------------------------------------------------------------------


def test_run_chat_action_resolves_stores_posts_and_narrates(tmp_path):
    from dungeon_daddy.rpg.service import RpgService

    orchestrator, ports, _repo, _ = _make(
        tmp_path, dungeon=_dungeon(), rpg_service=RpgService(),
    )

    orchestrator.run_chat_action("camp-1", "pc-1", "fight", "smash the door")

    assert len(ports.stored_results) == 1
    assert "outcome" in ports.stored_results[0]
    assert any(
        role == "system" and "Elara rolls FIGHT" in text
        for role, text in ports.messages
    )
    assert len(ports.narration_requests) == 1
    assert ports.narration_requests[0].startswith("Elara [FIGHT] smash the door —")
    assert ports.right_panel_refreshes == ["pc-1"]


def test_run_chat_action_without_service_posts_unavailable(tmp_path):
    orchestrator, ports, _repo, _ = _make(tmp_path)

    orchestrator.run_chat_action("camp-1", "pc-1", "fight", "smash")

    assert ports.messages == [("system", "RPG service unavailable.")]


def test_on_resolve_action_narrates_with_dice_and_refreshes(tmp_path):
    from dungeon_daddy.rpg.service import RpgService

    orchestrator, ports, _repo, _ = _make(
        tmp_path, dungeon=_dungeon(), rpg_service=RpgService(),
    )

    orchestrator.on_resolve_action(
        "camp-1", "pc-1", "climb the wall", "move",
        push_yourself=False, momentum_spend=0, dice_pool=2,
    )

    assert len(ports.stored_results) == 1
    assert len(ports.narration_requests) == 1
    msg = ports.narration_requests[0]
    assert msg.startswith("Elara [MOVE] climb the wall —")
    assert "dice=" in msg
    assert ports.right_panel_refreshes == ["pc-1"]


# ---------------------------------------------------------------------------
# run_proposal_pipeline / apply_obstacle_proposals — LLM proposals (Part B)
# ---------------------------------------------------------------------------


class _MockProvider:
    def __init__(self, response: str):
        self._response = response

    def complete(self, messages, system="", max_tokens=512):
        return self._response

    @property
    def model_id(self):
        return "mock"


def _resolution(outcome="full") -> Any:
    from dungeon_daddy.rpg.models import ActionResolution

    return ActionResolution(
        resolution_id="res-1", campaign_id="camp-1", actor_id="pc-1",
        action_key="skirmish", dice_rolled=[4, 5, 6], outcome=outcome,
        stress_cost=0, intent="disarm the guard",
    )


def test_run_proposal_pipeline_feeds_the_debug_sink(tmp_path):
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.rpg.service import RpgService
    from dungeon_daddy.ui.panels.debug_controls import DebugControls

    raw_json = '{"narration_hint": "Guards react.", "proposed_changes": []}'
    dm_agent = DungeonMasterAgent(provider=_MockProvider(raw_json))
    debug = DebugControls(RpgService())
    orchestrator, _ports, _repo, _ = _make(
        tmp_path, dm_agent=dm_agent, debug=debug,
    )

    orchestrator.run_proposal_pipeline(_resolution(), "camp-1")

    assert debug._last_validation is not None


def test_run_proposal_pipeline_noop_without_dm_agent_or_debug(tmp_path):
    orchestrator, ports, _repo, _ = _make(tmp_path)  # dm_agent=None, debug=None

    orchestrator.run_proposal_pipeline(_resolution(), "camp-1")

    assert ports.messages == []


def test_apply_obstacle_proposals_resolves_obstacle_on_resolving_outcome(tmp_path):
    from dungeon_daddy.rpg.proposal import ResolveObstacleChange
    from dungeon_daddy.rpg.proposal_validator import ValidationResult

    orchestrator, _ports, repo, _ = _make(tmp_path)
    _save_object_with_transition(
        repo, slug="gate", state="sealed", to_state="breached",
        trigger="force", contested=True, action_verb="fight",
    )
    result = ValidationResult(accepted=[
        ResolveObstacleChange(
            object_slug="gate", to_state="breached", reason="Rammed it open.",
        )
    ])

    orchestrator.apply_obstacle_proposals(result, "full", "pc-1")

    assert repo.get_room_object("obj-gate")["current_state"] == "breached"


def test_apply_obstacle_proposals_ignored_on_miss(tmp_path):
    from dungeon_daddy.rpg.proposal import ResolveObstacleChange
    from dungeon_daddy.rpg.proposal_validator import ValidationResult

    orchestrator, _ports, repo, _ = _make(tmp_path)
    _save_object_with_transition(
        repo, slug="gate", state="sealed", to_state="breached",
        trigger="force", contested=True, action_verb="fight",
    )
    result = ValidationResult(accepted=[
        ResolveObstacleChange(
            object_slug="gate", to_state="breached", reason="Rammed it open.",
        )
    ])

    orchestrator.apply_obstacle_proposals(result, "miss", "pc-1")

    assert repo.get_room_object("obj-gate")["current_state"] == "sealed"


# ---------------------------------------------------------------------------
# advance_objectives — §7.9 re-evaluation after a world-state mutation
# ---------------------------------------------------------------------------


def test_advance_objectives_posts_dungeon_bubble_per_completed_tier(tmp_path):
    orchestrator, ports, repo, _ = _make(tmp_path)
    _seed_intimacy_clock(repo)
    _save_subsystem(
        repo, slug="x", name="Gearworks", archetype="mechanism", state="restored",
    )
    _save_objective(repo, slug="clear-the-gearworks", tier=0, status="active")

    orchestrator.advance_objectives()

    assert ports.messages == [
        ("dungeon", "◆ The Crucible stirs — its bond with you deepens.")
    ]


# ---------------------------------------------------------------------------
# describe_spawned_loot — feed the revealed item to the DM narrator so its
# prose reflects reality (a container that spawns loot on open).
# ---------------------------------------------------------------------------


def test_describe_spawned_loot_empty_when_transition_spawns_nothing():
    assert describe_spawned_loot({"trigger": "open"}, []) == ""


def test_describe_spawned_loot_empty_when_item_not_in_room():
    transition = {"spawns_item_slug": "travel-journal"}
    assert describe_spawned_loot(transition, [{"slug": "other"}]) == ""


def test_describe_spawned_loot_names_and_describes_the_revealed_item():
    transition = {"spawns_item_slug": "travel-journal"}
    room_items = [
        {"slug": "travel-journal", "display_name": "Sun-Bleached Travel Journal",
         "description": "A dead scavenger's journal."},
    ]
    note = describe_spawned_loot(transition, room_items)
    assert "Sun-Bleached Travel Journal" in note
    assert "dead scavenger's journal" in note
