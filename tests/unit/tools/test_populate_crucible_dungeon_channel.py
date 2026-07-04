"""Tests for the Phase 51 dungeon-channel seed (`populate_crucible_dungeon_channel`).

Uses a real `MemoryRepository` on `tmp_path` (no mocks) and the real persona /
room-context / gate helpers, so the test proves the seed actually makes the
"Talk to the Dungeon" channel live end-to-end.
"""
from pathlib import Path

import pytest

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.dungeon_persona import (
    read_dungeon_knowledge,
    read_dungeon_voice,
)
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.dungeon_channel import (
    dungeon_channel_available,
    dungeon_systems_status,
    unlocked_knowledge,
)
from dungeon_daddy.rpg.models import ClockState, ObjectTransition, RoomObject
from dungeon_daddy.rpg.objectives import advance_objectives
from dungeon_daddy.rpg.obstacles import (
    obstacle_approach_verbs,
    obstacle_resolved_state,
)
from dungeon_daddy.rpg.room_context import build_room_context
from tools.populate_crucible_dungeon_channel import (
    CAMPAIGN_ID,
    INTIMACY_SEGMENTS,
    RESONANCE_ROOM_ID,
    seed_dungeon_channel,
)

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")


@pytest.fixture
def repo(tmp_path: Path):
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    r.save_campaign(
        campaign_id=CAMPAIGN_ID,
        slug="the-crucible",
        title="The Crucible",
        dungeon_slug="the-crucible",
    )
    yield r
    r.close()


def _intimacy_clock(repo: MemoryRepository) -> dict:
    return next(
        c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
    )


def test_seed_writes_persona_docs_and_campaign_refs(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    assert (tmp_path / "memory" / "dungeon" / "voice.md").exists()
    assert (tmp_path / "memory" / "dungeon" / "knowledge.md").exists()

    camp = repo.get_campaign(CAMPAIGN_ID)
    assert camp["dungeon_voice_path"] == "memory/dungeon/voice.md"
    assert camp["dungeon_knowledge_path"] == "memory/dungeon/knowledge.md"

    voice = read_dungeon_voice(tmp_path / camp["dungeon_voice_path"])
    assert voice and "forge" in voice.lower()
    secrets = read_dungeon_knowledge(tmp_path / camp["dungeon_knowledge_path"])
    assert len(secrets) >= 3


def test_seed_preserves_existing_campaign_fields(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    camp = repo.get_campaign(CAMPAIGN_ID)
    assert camp["slug"] == "the-crucible"
    assert camp["title"] == "The Crucible"
    assert camp["dungeon_slug"] == "the-crucible"


def test_seed_writes_latching_intimacy_clock(repo, tmp_path: Path):
    # Phase 51.5 D6: latching tier index — segments = #tiers, filled = #completed.
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    clock = _intimacy_clock(repo)
    assert clock["monotonic"] is True
    assert clock["segments"] == 4
    assert clock["filled"] == 0
    assert clock["clock_level"] == "dungeon"


def test_seed_opens_channel_at_resonance_room(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    objs = repo.get_objects_by_room(CAMPAIGN_ID, RESONANCE_ROOM_ID)
    assert any(o["archetype"] == "resonance_point" for o in objs)

    ctx = build_room_context(
        RESONANCE_ROOM_ID,
        CAMPAIGN_ID,
        SessionState(dungeon_id="the-crucible"),
        repo,
    )
    assert ctx["resonance_point"] is True

    row = _intimacy_clock(repo)
    clock = ClockState(
        clock_id=row["clock_id"],
        campaign_id=row["campaign_id"],
        label=row["label"],
        segments=row["segments"],
        filled=row["filled"],
        status=row["status"],
        clock_level=row["clock_level"],
        category=row["category"],
        monotonic=row["monotonic"],
    )
    ok, reason = dungeon_channel_available(ctx, clock)
    assert ok is True
    assert reason is None


def test_seed_is_idempotent(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    clocks = [
        c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
    ]
    assert len(clocks) == 1
    objs = [
        o
        for o in repo.get_objects_by_room(CAMPAIGN_ID, RESONANCE_ROOM_ID)
        if o["archetype"] == "resonance_point"
    ]
    assert len(objs) == 1
    # No duplicate objectives or subsystems on a second run.
    assert len(repo.get_objectives(CAMPAIGN_ID)) == INTIMACY_SEGMENTS
    slugs = [o["slug"] for o in repo.get_objects_for_campaign(CAMPAIGN_ID)]
    assert len(slugs) == len(set(slugs))


def test_seed_adopts_existing_intimacy_clock(repo, tmp_path: Path):
    # The canonical RPG seed authors a monotonic dungeon_intimacy clock; the
    # channel seed must adopt it (flip monotonic, open it) — not create a second.
    repo.save_clock(
        clock_id="clock:the-crucible:the-dungeon-learns-you",
        campaign_id=CAMPAIGN_ID,
        label="The Factory Learns What You Fear",
        segments=6,
        filled=2,
        category="dungeon_intimacy",
        clock_level="dungeon",
        monotonic=True,
    )

    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    clocks = [
        c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
    ]
    assert len(clocks) == 1
    clock = clocks[0]
    assert clock["clock_id"] == "clock:the-crucible:the-dungeon-learns-you"
    assert clock["label"] == "The Factory Learns What You Fear"
    assert clock["monotonic"] is True  # reverted to latching (D6)
    assert clock["segments"] == 4  # re-segmented from 6 to #tiers
    assert clock["filled"] == 0  # no objectives completed yet


# --- Slice 10: the intimacy ladder ----------------------------------------


def _add_gearworks(repo: MemoryRepository, state: str = "jammed") -> str:
    """Add the tier-0 target (the existing Sand-Choked Gearworks); return its id."""
    object_id = "object:the-crucible:R4:gearworks"
    repo.save_room_object(
        RoomObject(
            object_id=object_id,
            campaign_id=CAMPAIGN_ID,
            room_id="R4",
            level_id="level:1",
            slug="gearworks",
            display_name="Sand-Choked Gearworks",
            archetype="structure",
            description="The primary intake, packed solid with red sand.",
            current_state=state,
            transitions=[],
        )
    )
    return object_id


def test_seed_authors_four_objectives(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    objs = repo.get_objectives(CAMPAIGN_ID)
    assert [o["tier_index"] for o in objs] == [0, 1, 2, 3]
    assert objs[0]["status"] == "active"  # tier 0 starts active
    assert [o["status"] for o in objs[1:]] == ["locked", "locked", "locked"]
    for o in objs:
        assert o["advances_clock_slug"] == "dungeon_intimacy"
        assert o["completion"]["kind"] == "object_state"
        assert o["completion"]["required_state"]
        assert o["reveals_knowledge"]  # every tier authors at least one secret


def test_seed_authors_fresh_subsystems(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    by_slug = {o["slug"]: o for o in repo.get_objects_for_campaign(CAMPAIGN_ID)}

    assert by_slug["coolant-loop"]["current_state"] == "ruptured"
    assert by_slug["coolant-loop"]["archetype"] == "structure"
    assert by_slug["arcane-conduits"]["current_state"] == "dormant"
    assert by_slug["core-containment"]["current_state"] == "failing"

    # Each fresh subsystem has a restore transition to its objective's target state.
    loop_targets = {t["to_state"] for t in by_slug["coolant-loop"]["transitions"]}
    assert "restored" in loop_targets

    # They surface in the dungeon's truthful systems status.
    names = [n for n, _ in dungeon_systems_status(repo.get_objects_for_campaign(CAMPAIGN_ID))]
    assert "Coolant Loop Manifold" in names


def test_seed_authors_contested_approaches_on_subsystems(repo, tmp_path: Path):
    # Phase 51.5 Part A Slice 4: each fresh subsystem is an obstacle solvable by
    # multiple class-flavored, contested approaches that converge on its resolved
    # state (so any path completes the objective the same way).
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    by_slug = {
        o["slug"]: RoomObject(**o) for o in repo.get_objects_for_campaign(CAMPAIGN_ID)
    }

    loop = by_slug["coolant-loop"]
    loop_verbs = obstacle_approach_verbs(loop)
    assert len(loop_verbs) >= 2
    assert obstacle_resolved_state(loop) == "restored"
    assert "fight" not in loop_verbs  # thematic: no brute force on delicate piping

    assert obstacle_resolved_state(by_slug["arcane-conduits"]) == "charged"
    assert len(obstacle_approach_verbs(by_slug["arcane-conduits"])) >= 2
    assert obstacle_resolved_state(by_slug["core-containment"]) == "stabilized"
    assert len(obstacle_approach_verbs(by_slug["core-containment"])) >= 2


def test_reseed_upgrades_legacy_subsystem_to_contested_approaches(repo, tmp_path: Path):
    # A pre-Slice-4 subsystem (present with a single deterministic transition) is
    # upgraded to contested approaches on reseed — additively: its played state is
    # preserved, not reset.
    object_id = "object:the-crucible:r02:coolant-loop"
    repo.save_room_object(
        RoomObject(
            object_id=object_id,
            campaign_id=CAMPAIGN_ID,
            room_id="r02",
            level_id="level:2",
            slug="coolant-loop",
            display_name="Coolant Loop Manifold",
            archetype="structure",
            description="A legacy, single-transition version.",
            current_state="ruptured",
            transitions=[
                ObjectTransition(
                    transition_id=f"{object_id}:restore",
                    object_id=object_id,
                    from_state="ruptured",
                    to_state="restored",
                    trigger="activate",
                )
            ],
        )
    )

    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    loop = next(
        RoomObject(**o)
        for o in repo.get_objects_for_campaign(CAMPAIGN_ID)
        if o["slug"] == "coolant-loop"
    )
    assert loop.current_state == "ruptured"  # state preserved (additive)
    assert len(obstacle_approach_verbs(loop)) >= 2  # upgraded to contested approaches


def test_seed_adopts_existing_gearworks_for_tier_zero(repo, tmp_path: Path):
    # Tier 0 targets the pre-existing Sand-Choked Gearworks; the channel seed must
    # not author (and so risk clobbering) it.
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    slugs = {o["slug"] for o in repo.get_objects_for_campaign(CAMPAIGN_ID)}
    assert "gearworks" not in slugs
    tier0 = next(o for o in repo.get_objectives(CAMPAIGN_ID) if o["tier_index"] == 0)
    assert tier0["completion"]["target_slug"] == "gearworks"


def test_reseed_preserves_completed_objective(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    tier0 = next(o for o in repo.get_objectives(CAMPAIGN_ID) if o["tier_index"] == 0)
    repo.update_objective_status(tier0["objective_id"], "completed")

    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    objs = {o["slug"]: o for o in repo.get_objectives(CAMPAIGN_ID)}
    assert objs["clear-the-gearworks"]["status"] == "completed"
    # The latching clock fill follows the completed-objective count.
    assert _intimacy_clock(repo)["filled"] == 1


def test_reseed_does_not_reset_restored_subsystem(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    loop = next(
        o for o in repo.get_objects_for_campaign(CAMPAIGN_ID) if o["slug"] == "coolant-loop"
    )
    repo.update_object_state(loop["object_id"], "restored")

    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    loop = next(
        o for o in repo.get_objects_for_campaign(CAMPAIGN_ID) if o["slug"] == "coolant-loop"
    )
    assert loop["current_state"] == "restored"  # preserved, not reset to ruptured


def test_completing_a_subsystem_advances_the_ladder(repo, tmp_path: Path):
    # End-to-end: restoring the tier-0 subsystem in the engine drives the real
    # objective service — completes the tier, ticks the latching clock, activates
    # the next tier, and unlocks the tier's secret.
    gear_id = _add_gearworks(repo, "jammed")
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    assert _intimacy_clock(repo)["filled"] == 0

    repo.update_object_state(gear_id, "cleared")  # the player fixes it
    results = advance_objectives(repo, CAMPAIGN_ID)

    assert len(results) == 1
    objs = {o["slug"]: o for o in repo.get_objectives(CAMPAIGN_ID)}
    assert objs["clear-the-gearworks"]["status"] == "completed"
    assert objs["restore-the-coolant-loop"]["status"] == "active"  # next tier opened
    assert _intimacy_clock(repo)["filled"] == 1

    unlocked = unlocked_knowledge(repo.get_objectives(CAMPAIGN_ID))
    assert any("red sand" in s for s in unlocked)  # tier-0 secret revealed
    assert not any("elemental heart" in s for s in unlocked)  # deep tiers stay gated
