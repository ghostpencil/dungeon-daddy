"""Phase 51.5 Part B Slice 6 — a DM-ruled ``ResolveObstacleChange`` proposal,
once validated, resolves the obstacle through the deterministic ``ActivateObject``
pipeline (so side-effects fire and objectives re-advance), gated on the roll
outcome.

Drives the real ``_run_proposal_pipeline`` — the only mock is ``_dm_agent`` (the
LLM, mandatory) and ``_rpg_debug`` (a UI panel). The obstacle-state map is built
from the real room objects and passed to the real ``validate_proposal``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    Objective,
    ObjectiveCompletion,
    ObjectTransition,
    RoomObject,
)

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)


def _actor() -> ActorState:
    return ActorState(
        actor_id="pc-1", campaign_id="camp-1", actor_type="pc",
        slug="kira", display_name="Kira", status="active",
        actions={"tinker": 2}, playbook_slug="artificer",
    )


def _make_view(tmp_path: Path):
    from dungeon_daddy.views.play_view import PlayView
    from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel
    from dungeon_daddy.ui.player_action_state import PlayerActionState

    repo = MemoryRepository(tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    actor = _actor()
    view = PlayView.__new__(PlayView)
    view._mem_repo = repo
    view._rpg_campaign_id = "camp-1"
    view._state = SessionState(
        dungeon_id="d1", current_level_idx=0,
        current_room_id="r1", visited_rooms=["r1"],
    )
    view._dungeon = None
    view._chat = MagicMock()
    view._rpg_vna = VnaActionPanel()
    view._rpg_action = MagicMock(_actors=[actor])
    view._action_state = PlayerActionState()
    view._action_state.set_actor_roster([actor.actor_id])
    view._dm_agent = MagicMock()
    view._rpg_debug = MagicMock()
    return view


def _seed_obstacle(repo: MemoryRepository, current_state: str = "jammed") -> None:
    repo.save_room_object(RoomObject(
        object_id="gearworks", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="gearworks", display_name="Seized Gearworks", archetype="mechanism",
        description="A jammed tangle of brass gears.", current_state=current_state,
        transitions=[ObjectTransition(
            transition_id="tr:tinker", object_id="gearworks",
            from_state="jammed", to_state="cleared", trigger="tinker",
            contested=True, action_verb="tinker",
        )],
    ))


def _seed_gated_objective(repo: MemoryRepository) -> None:
    repo.save_clock(
        clock_id="clk:camp-1:dungeon_intimacy", campaign_id="camp-1",
        label="Intimacy", segments=4, filled=0, category="dungeon_intimacy",
        monotonic=True,
    )
    repo.save_objective(Objective(
        objective_id="obj:clear", campaign_id="camp-1", slug="clear-the-gearworks",
        title="Clear the Gearworks", description="Free the seized gears.",
        tier_index=0, status="active",
        completion=ObjectiveCompletion(
            kind="object_state", target_slug="gearworks", required_state="cleared",
        ),
        advances_clock_slug="dungeon_intimacy",
    ))


def _resolution(outcome: str) -> ActionResolution:
    return ActionResolution(
        resolution_id="res-1", campaign_id="camp-1", actor_id="pc-1",
        action_key="endure", dice_rolled=[6], outcome=outcome, intent=None,
    )


def _resolve_obstacle_raw(to_state: str = "cleared") -> str:
    return json.dumps({
        "narration_hint": "The barbarian pries the seized gears loose.",
        "proposed_changes": [{
            "kind": "resolve_obstacle",
            "object_slug": "gearworks",
            "to_state": to_state,
            "reason": "brute force wrenched the jam free",
        }],
        "source": "llm_draft",
    })


def test_full_success_proposal_clears_obstacle_and_completes_objective(tmp_path):
    view = _make_view(tmp_path)
    repo = view._mem_repo
    _seed_obstacle(repo)
    _seed_gated_objective(repo)
    view._dm_agent.request_proposal.return_value = _resolve_obstacle_raw()

    view._run_proposal_pipeline(_resolution("full"), "camp-1")

    assert repo.get_room_object("gearworks")["current_state"] == "cleared"
    assert repo.get_objectives("camp-1")[0]["status"] == "completed"


def test_miss_leaves_obstacle_unchanged_even_when_proposed(tmp_path):
    view = _make_view(tmp_path)
    repo = view._mem_repo
    _seed_obstacle(repo)
    view._dm_agent.request_proposal.return_value = _resolve_obstacle_raw()

    view._run_proposal_pipeline(_resolution("miss"), "camp-1")

    assert repo.get_room_object("gearworks")["current_state"] == "jammed"


def test_unauthored_to_state_is_rejected_and_leaves_obstacle_unchanged(tmp_path):
    view = _make_view(tmp_path)
    repo = view._mem_repo
    _seed_obstacle(repo)
    # LLM tries to invent a resolved state the obstacle does not author.
    view._dm_agent.request_proposal.return_value = _resolve_obstacle_raw(to_state="obliterated")

    view._run_proposal_pipeline(_resolution("full"), "camp-1")

    assert repo.get_room_object("gearworks")["current_state"] == "jammed"
