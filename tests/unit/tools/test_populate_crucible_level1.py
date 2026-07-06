"""Tests for the Crucible Level-1 seed (`populate_crucible_level1`).

Phase 51.5 Part A Slice 4 focus: the tier-0 Sand-Choked Gearworks is an
*obstacle* — solvable by multiple class-flavored, contested approaches that all
converge on one resolved state — and reseeding is additive (it never resets a
subsystem the party has already changed). Real `MemoryRepository` on `tmp_path`,
no mocks.
"""
from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.obstacles import (
    obstacle_approach_verbs,
    obstacle_resolved_state,
)
from tools.populate_crucible_level1 import (
    CAMPAIGN_ID,
    _items,
    _objects,
    _oid,
    save_objects_preserving_state,
)

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")

# The nine core action ratings — an approach verb must be one of these so an
# actor can actually attempt it.
_CORE_VERBS = {
    "fight", "endure", "move", "tinker", "study", "focus", "sway", "sense", "channel",
}


def _gearworks():
    return next(o for o in _objects() if o.slug == "gearworks")


def test_gearworks_is_a_contested_obstacle_converging_on_cleared():
    gear = _gearworks()
    assert gear.current_state == "jammed"
    verbs = obstacle_approach_verbs(gear)
    # Multiple class-flavored ways to clear it (thematic: tinker / fight / endure).
    assert len(verbs) >= 2
    assert set(verbs) <= _CORE_VERBS
    # All approaches converge on the one resolved state (#1 normalize completion).
    assert obstacle_resolved_state(gear) == "cleared"


def _supply_locker():
    return next(o for o in _objects() if o.slug == "supply-locker")


def _travel_journal():
    return next(i for i in _items() if i.slug == "travel-journal")


def test_supply_locker_spawns_the_travel_journal_when_opened_or_forced():
    # The journal is the locker's reward — opening OR forcing it reveals the item,
    # rewarding the player's curiosity rather than leaving it loose in R1.
    locker = _supply_locker()
    triggers = {t.trigger for t in locker.transitions}
    assert triggers == {"open", "force"}
    assert all(t.spawns_item_slug == "travel-journal" for t in locker.transitions)


def test_travel_journal_starts_unplaced_inert_inside_the_locker():
    # Not loose in the room: it must be an unplaced, inert item so the locker's
    # spawn (owner is None AND room_id is None) can place it on open.
    journal = _travel_journal()
    assert journal.room_id is None
    assert journal.owner_actor_id is None
    assert journal.status == "inert"


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


def test_reseed_preserves_played_object_state(repo):
    save_objects_preserving_state(repo, _objects())
    gear_id = _oid("R4", "gearworks")
    repo.update_object_state(gear_id, "cleared")  # the party clears it

    save_objects_preserving_state(repo, _objects())  # additive reseed

    assert repo.get_room_object(gear_id)["current_state"] == "cleared"


# --- Slice 9: the World Reaction Policy map (design §6) --------------------

# Plot gates, the intimacy-chain obstacle, and hazards get deterministic
# `scripted` control; scenery / lore / containers stay on the loose `ambient`
# path (the default).
_SCRIPTED_L1 = {"great-lift", "gearworks", "spike-plates", "dart-vents", "trap-lever"}
_AMBIENT_L1 = {
    "toppled-statue", "supply-locker", "market-stall",
    "notice-board", "cargo-crate", "manifest-terminal",
}

# Firewalled clock categories (§3) may never be named by a scripted binding —
# they move only via their own service (dungeon_intimacy → objective service, D5).
_FIREWALLED_CLOCK_SLUGS = {
    "the-dungeon-learns-you",      # dungeon_intimacy
    "restore-the-power-core",      # objective
    "mira-guild-agenda-surfaces",  # relationship
    "djinn-reclaims-the-engines",  # faction_pressure
}


def _by_slug():
    return {o.slug: o for o in _objects()}


def test_policies_match_the_design_map():
    by = _by_slug()
    for slug in _SCRIPTED_L1:
        assert by[slug].reaction_policy == "scripted", slug
    for slug in _AMBIENT_L1:
        assert by[slug].reaction_policy == "ambient", slug


def test_hazard_bindings_apply_authored_body_stress_on_a_botched_handling():
    by = _by_slug()
    spikes = [
        (b.action_verb, b.outcome, b.stress_track, b.stress_amount)
        for b in by["spike-plates"].reaction_bindings
    ]
    assert spikes == [("*", "miss", "body", 2)]  # heavy spikes
    darts = [
        (b.action_verb, b.outcome, b.stress_track, b.stress_amount)
        for b in by["dart-vents"].reaction_bindings
    ]
    assert darts == [("*", "miss", "body", 1)]  # lighter needle darts


def test_gate_bindings_move_one_local_adverse_clock_no_fan_out():
    by = _by_slug()
    lift = [
        (b.action_verb, b.outcome, b.clock_slug, b.clock_delta)
        for b in by["great-lift"].reaction_bindings
    ]
    assert lift == [("*", "miss", "arcane-overload-building", 1)]
    gear = [
        (b.action_verb, b.outcome, b.clock_slug, b.clock_delta)
        for b in by["gearworks"].reaction_bindings
    ]
    assert gear == [("*", "miss", "party-detected", 1)]
    # The trap-lever is pure deterministic control — scripted, no reaction binding.
    assert by["trap-lever"].reaction_bindings == []


def test_no_binding_targets_a_firewalled_clock():
    for o in _objects():
        for b in o.reaction_bindings:
            assert b.clock_slug not in _FIREWALLED_CLOCK_SLUGS, (o.slug, b.clock_slug)
