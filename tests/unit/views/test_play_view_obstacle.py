"""Phase 51.5 Part A Slice 2 — a successful contested-approach roll changes
object state and re-runs objective advancement.

`_maybe_resolve_obstacle` is the testable seam `_resolve_vna_roll` calls with the
roll outcome, keeping the random dice roll out of the test.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.action_options import ActionCard
from dungeon_daddy.rpg.models import (
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


def test_full_success_clears_obstacle_and_completes_objective(tmp_path):
    view = _make_view(tmp_path)
    repo = view._mem_repo
    _seed_obstacle(repo)
    _seed_gated_objective(repo)

    card = ActionCard(verb="tinker", noun_id="gearworks", adverb="carefully")
    res = view._maybe_resolve_obstacle(card, _actor(), outcome="full")

    assert res is not None
    assert repo.get_room_object("gearworks")["current_state"] == "cleared"
    objective = repo.get_objectives("camp-1")[0]
    assert objective["status"] == "completed"


def test_partial_success_resolves_with_complication(tmp_path):
    view = _make_view(tmp_path)
    _seed_obstacle(view._mem_repo)

    card = ActionCard(verb="tinker", noun_id="gearworks", adverb="carefully")
    res = view._maybe_resolve_obstacle(card, _actor(), outcome="partial")

    assert res is not None
    assert res.complication is True
    assert view._mem_repo.get_room_object("gearworks")["current_state"] == "cleared"


def test_miss_leaves_object_state_unchanged(tmp_path):
    view = _make_view(tmp_path)
    _seed_obstacle(view._mem_repo)

    card = ActionCard(verb="tinker", noun_id="gearworks", adverb="carefully")
    res = view._maybe_resolve_obstacle(card, _actor(), outcome="miss")

    assert res is None
    assert view._mem_repo.get_room_object("gearworks")["current_state"] == "jammed"
