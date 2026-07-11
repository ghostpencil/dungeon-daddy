"""Unit tests for :class:`PlaySessionContext` (Phase 51.7, Slice 0).

The context is the single source of truth for the live play session's dungeon,
session state, repo/campaign handles, and the actor roster. It replaces the
``dungeon → level → room`` lookup idiom (duplicated ~9× in ``play_view``) and the
``PlayerActionPanel._actors`` reach-ins (finding 1 & 2 of the phase audit).
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
from dungeon_daddy.play.session_context import ActiveCampaign, PlaySessionContext
from dungeon_daddy.rpg.models import ActorState
from tests.unit.play._factories import MIGRATIONS_DIR


def _rooms() -> list[Room]:
    return [
        Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note=""),
        Room(id="1-B", num=2, name="Guard Post", x=5, y=0, w=4, h=3, type="shrine", note=""),
    ]


def _level(level_id: int = 1) -> Level:
    return Level(
        id=level_id, name=f"Level {level_id}", summary="", ecology="", loop="lock_key",
        width=12, height=10, entries=[], rooms=_rooms(),
        connections=[Connection(from_room="1-A", to_room="1-B", type="door")],
    )


def _dungeon(num_levels: int = 2) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="", setting="", party="", quest=""),
        levels=[_level(i + 1) for i in range(num_levels)],
    )


def _actor(actor_id: str, name: str) -> ActorState:
    return ActorState(
        actor_id=actor_id, campaign_id="camp-1", actor_type="pc",
        slug=actor_id, display_name=name, status="active",
    )


# --- current_level() ---------------------------------------------------------

def test_current_level_returns_level_at_state_index() -> None:
    ctx = PlaySessionContext(
        dungeon=_dungeon(), state=SessionState(dungeon_id="d", current_level_idx=1)
    )
    level = ctx.current_level()
    assert level is not None
    assert level.id == 2


def test_current_level_is_none_without_dungeon_or_state() -> None:
    assert PlaySessionContext().current_level() is None
    assert PlaySessionContext(dungeon=_dungeon()).current_level() is None
    assert PlaySessionContext(
        state=SessionState(dungeon_id="d")
    ).current_level() is None


def test_current_level_is_none_when_index_out_of_range() -> None:
    ctx = PlaySessionContext(
        dungeon=_dungeon(num_levels=1),
        state=SessionState(dungeon_id="d", current_level_idx=3),
    )
    assert ctx.current_level() is None


# --- current_room() ----------------------------------------------------------

def test_current_room_resolves_from_state_room_id() -> None:
    ctx = PlaySessionContext(
        dungeon=_dungeon(),
        state=SessionState(dungeon_id="d", current_level_idx=0, current_room_id="1-B"),
    )
    room = ctx.current_room()
    assert room is not None
    assert room.name == "Guard Post"


def test_current_room_is_none_without_room_id() -> None:
    ctx = PlaySessionContext(
        dungeon=_dungeon(), state=SessionState(dungeon_id="d", current_level_idx=0)
    )
    assert ctx.current_room() is None


def test_current_room_is_none_for_unknown_room_id() -> None:
    ctx = PlaySessionContext(
        dungeon=_dungeon(),
        state=SessionState(dungeon_id="d", current_level_idx=0, current_room_id="nope"),
    )
    assert ctx.current_room() is None


# --- current_level_id (synthesized) -----------------------------------------

def test_current_level_id_is_one_based_synthesized_string() -> None:
    """Pins the ``f"level-{idx+1}"`` convention the world-reaction level scope
    relies on (guarded end-to-end by test_play_view_bundle)."""
    ctx = PlaySessionContext(state=SessionState(dungeon_id="d", current_level_idx=0))
    assert ctx.current_level_id == "level-1"
    ctx.state = SessionState(dungeon_id="d", current_level_idx=1)
    assert ctx.current_level_id == "level-2"


def test_current_level_id_is_none_without_state() -> None:
    assert PlaySessionContext().current_level_id is None


# --- roster ------------------------------------------------------------------

def test_actors_defaults_empty_and_set_actors_copies() -> None:
    ctx = PlaySessionContext()
    assert ctx.actors == []
    source = [_actor("a1", "Vex")]
    ctx.set_actors(source)
    assert [a.actor_id for a in ctx.actors] == ["a1"]
    # stored as its own list, not an alias of the caller's
    source.append(_actor("a2", "Bram"))
    assert [a.actor_id for a in ctx.actors] == ["a1"]


def test_actors_can_be_seeded_at_construction() -> None:
    ctx = PlaySessionContext(actors=[_actor("a1", "Vex"), _actor("a2", "Bram")])
    assert [a.actor_id for a in ctx.actors] == ["a1", "a2"]


# --- acting_actor ------------------------------------------------------------

def test_acting_actor_returns_selected_when_present() -> None:
    ctx = PlaySessionContext(actors=[_actor("a1", "Vex"), _actor("a2", "Bram")])
    acting = ctx.acting_actor("a2")
    assert acting is not None
    assert acting.actor_id == "a2"


def test_acting_actor_falls_back_to_first_pc() -> None:
    ctx = PlaySessionContext(actors=[_actor("a1", "Vex"), _actor("a2", "Bram")])
    assert ctx.acting_actor(None).actor_id == "a1"  # type: ignore[union-attr]
    assert ctx.acting_actor("gone").actor_id == "a1"  # type: ignore[union-attr]


def test_acting_actor_is_none_when_roster_empty() -> None:
    assert PlaySessionContext().acting_actor("a1") is None


# --- active_campaign() -------------------------------------------------------

def _repo(tmp_path: Path) -> MemoryRepository:
    repo = MemoryRepository(tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_campaign("camp-1", "test-campaign", "Test Campaign")
    return repo


def test_active_campaign_returns_value_when_repo_and_id_present(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    ctx = PlaySessionContext(mem_repo=repo, campaign_id="camp-1")
    active = ctx.active_campaign()
    assert active is not None
    assert active.repo is repo
    assert active.campaign_id == "camp-1"


def test_active_campaign_is_none_without_repo(tmp_path: Path) -> None:
    ctx = PlaySessionContext(campaign_id="camp-1")
    assert ctx.active_campaign() is None


def test_active_campaign_is_none_without_campaign_id(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    ctx = PlaySessionContext(mem_repo=repo)
    assert ctx.active_campaign() is None


def test_active_campaign_is_frozen_value() -> None:
    active = ActiveCampaign(repo=None, campaign_id="camp-1")  # type: ignore[arg-type]
    try:
        active.campaign_id = "other"  # type: ignore[misc]
    except Exception as exc:  # frozen dataclass raises FrozenInstanceError
        assert "FrozenInstanceError" in type(exc).__name__
    else:  # pragma: no cover - guard against a mutable value slipping in
        raise AssertionError("ActiveCampaign should be immutable")
