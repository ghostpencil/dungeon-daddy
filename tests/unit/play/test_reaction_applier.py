"""Unit tests for the world-reaction applier (Phase 51.7, Slice 1)."""
from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.play.reaction_applier import ReactionApplier
from dungeon_daddy.play.session_context import PlaySessionContext
from dungeon_daddy.rpg.models import (
    ActionResolution,
    ActorState,
    ReactionClockLine,
    ReactionStressLine,
    StressTrack,
    WorldReaction,
)
from tests.unit.play._factories import MIGRATIONS_DIR


def _resolution() -> ActionResolution:
    return ActionResolution(
        resolution_id="r1", campaign_id="camp-1", actor_id="a-pc",
        action_key="study", dice_rolled=[2], outcome="miss",
    )


def _reaction(*, clock_filled: int = 3, stress_filled: int = 2) -> WorldReaction:
    return WorldReaction(
        reaction_id="rx1", campaign_id="camp-1", source_resolution_id="r1",
        outcome="miss",
        clock_lines=[
            ReactionClockLine(
                clock_id="clk", label="Doom", ticks=1,
                new_filled=clock_filled, new_status="active", reason="miss",
            )
        ],
        stress_lines=[
            ReactionStressLine(
                actor_id="a-pc", display_name="Elara", track_key="body",
                amount=1, new_filled=stress_filled, reason="miss",
            )
        ],
    )


def _applier(tmp_path: Path, reaction: WorldReaction):
    """A ReactionApplier wired to a real repo/context; reaction is injected."""
    repo = MemoryRepository(db_path=tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_clock("clk", "camp-1", "Doom", segments=6, filled=0)
    repo.save_actor("a-pc", "camp-1", "pc", "hero", "Elara")
    repo.save_actor_stress_track("a-pc", "body", capacity=4, filled=0)

    actor = ActorState(
        actor_id="a-pc", campaign_id="camp-1", actor_type="pc",
        slug="hero", display_name="Elara",
        stress={"body": StressTrack(track_key="body", capacity=4, filled=0)},
    )
    session = PlaySessionContext(
        state=SessionState(
            dungeon_id="camp-1", current_level_idx=0, current_room_id="r1",
        ),
        mem_repo=repo,
        campaign_id="camp-1",
        actors=[actor],
    )
    service = MagicMock()
    service.react_to_resolution.return_value = (reaction, MagicMock())
    posted: list[str] = []
    applier = ReactionApplier(
        session, service, post_system=posted.append,
    )
    return applier, session, repo, posted


def test_applies_clock_and_stress_writes(tmp_path: Path) -> None:
    applier, _session, repo, posted = _applier(tmp_path, _reaction())

    result = applier.apply(_resolution())

    clocks = {c["clock_id"]: c["filled"] for c in repo.get_clocks("camp-1")}
    tracks = {t["track_key"]: t["filled"] for t in repo.get_actor_stress_tracks("a-pc")}
    assert clocks["clk"] == 3
    assert tracks["body"] == 2
    assert result is not None
    assert posted == []


def test_mid_write_failure_rolls_back_and_posts_failure_line(tmp_path: Path) -> None:
    from dungeon_daddy.play.reaction_applier import REACTION_FAILURE_LINE

    applier, _session, repo, posted = _applier(tmp_path, _reaction())
    # Simulate a DB error *after* the clock write, mid-transaction.
    repo.save_actor_stress_track = MagicMock(side_effect=RuntimeError("db down"))

    result = applier.apply(_resolution())

    clocks = {c["clock_id"]: c["filled"] for c in repo.get_clocks("camp-1")}
    assert clocks["clk"] == 0, "the clock write must be rolled back — no partial state"
    assert result is None
    assert posted == [REACTION_FAILURE_LINE]


def test_returns_none_without_service_or_repo(tmp_path: Path) -> None:
    applier, session, _repo, posted = _applier(tmp_path, _reaction())
    session.mem_repo = None

    assert applier.apply(_resolution()) is None
    assert posted == []


def test_compute_failure_degrades_silently(tmp_path: Path) -> None:
    """A compute-time failure (no DB write) must NOT post the write-failure
    line — nothing was applied, so it degrades silently as before."""
    applier, _session, _repo, posted = _applier(tmp_path, _reaction())
    applier._rpg_service.react_to_resolution.side_effect = RuntimeError("compute")

    assert applier.apply(_resolution()) is None
    assert posted == []


def test_read_failure_does_not_crash_or_post(tmp_path: Path) -> None:
    """A read-time DB failure must be contained (no uncaught exception) and,
    since nothing was written, must not post the write-failure line."""
    applier, _session, repo, posted = _applier(tmp_path, _reaction())
    repo.get_clocks = MagicMock(side_effect=RuntimeError("db read down"))

    assert applier.apply(_resolution()) is None
    assert posted == []


def test_new_stress_track_synced_to_in_memory_actor(tmp_path: Path) -> None:
    """A stress line for a track the actor lacks is mirrored into actor.stress
    (not just the DB), so the party panel reflects it without a reload."""
    reaction = WorldReaction(
        reaction_id="rx1", campaign_id="camp-1", source_resolution_id="r1",
        outcome="miss",
        stress_lines=[
            ReactionStressLine(
                actor_id="a-pc", display_name="Elara", track_key="weird",
                amount=1, new_filled=1, reason="miss",
            )
        ],
    )
    applier, session, repo, _posted = _applier(tmp_path, reaction)

    applier.apply(_resolution())

    actor = session.actors[0]
    assert "weird" in actor.stress
    assert actor.stress["weird"].filled == 1
    tracks = {t["track_key"]: t for t in repo.get_actor_stress_tracks("a-pc")}
    assert tracks["weird"]["filled"] == 1
