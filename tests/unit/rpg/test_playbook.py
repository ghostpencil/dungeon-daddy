"""Unit tests for rpg/playbook.py — Pydantic schema + validation."""
import pytest
from pydantic import ValidationError

from dungeon_daddy.rpg.playbook import (
    Playbook,
    PlaybookAbility,
    PlaybookKit,
    PlaybookLibrary,
    PlaybookStressTrack,
    SignatureAdverb,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kit(abilities: list[PlaybookAbility] | None = None) -> PlaybookKit:
    return PlaybookKit(
        slug="combat-gear",
        display_name="Combat Gear",
        description="A fighter's standard loadout.",
        charges_max=3,
        abilities=abilities or [],
    )


def _ability(slug: str = "rally") -> PlaybookAbility:
    return PlaybookAbility(
        slug=slug,
        display_name=slug.title(),
        description=f"{slug} description",
    )


def _valid_playbook(**overrides) -> dict:
    base = {
        "slug": "fighter",
        "display_name": "Fighter",
        "starting_action_ratings": {"fight": 2, "endure": 1},
        "starting_stress_tracks": [
            {"track_key": "body", "capacity": 4},
            {"track_key": "composure", "capacity": 4},
        ],
        "starting_kit": _kit(),
        "tags": ["warrior"],
        "signature_adverbs": [
            {"slug": "recklessly", "target_types": ["monster"]},
        ],
        "starting_abilities": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Cycle 1 — tracer bullet: valid Playbook constructs
# ---------------------------------------------------------------------------

def test_valid_playbook_constructs() -> None:
    pb = Playbook(**_valid_playbook())
    assert pb.slug == "fighter"
    assert pb.starting_action_ratings["fight"] == 2
    assert pb.ability_pool == []
    assert pb.beats == []


# ---------------------------------------------------------------------------
# Cycle 2 — unknown action key rejected
# ---------------------------------------------------------------------------

def test_unknown_action_key_raises() -> None:
    with pytest.raises(ValidationError, match="starting_action_ratings"):
        Playbook(**_valid_playbook(starting_action_ratings={"punch": 2}))


# ---------------------------------------------------------------------------
# Cycle 3 — rating out of range (high)
# ---------------------------------------------------------------------------

def test_rating_above_max_raises() -> None:
    with pytest.raises(ValidationError, match="starting_action_ratings"):
        Playbook(**_valid_playbook(starting_action_ratings={"fight": 4}))


# ---------------------------------------------------------------------------
# Cycle 4 — rating out of range (low)
# ---------------------------------------------------------------------------

def test_rating_below_zero_raises() -> None:
    with pytest.raises(ValidationError, match="starting_action_ratings"):
        Playbook(**_valid_playbook(starting_action_ratings={"fight": -1}))


# ---------------------------------------------------------------------------
# Cycle 5 — invalid stress track key
# ---------------------------------------------------------------------------

def test_invalid_track_key_raises() -> None:
    with pytest.raises(ValidationError, match="track_key"):
        PlaybookStressTrack(track_key="courage", capacity=4)


# ---------------------------------------------------------------------------
# Cycle 6 — invalid target_type in SignatureAdverb
# ---------------------------------------------------------------------------

def test_invalid_adverb_target_type_raises() -> None:
    with pytest.raises(ValidationError, match="target_types"):
        SignatureAdverb(slug="recklessly", target_types=["dragon"])


# ---------------------------------------------------------------------------
# Cycle 7 — starting_abilities slug must resolve in kit ∪ pool
# ---------------------------------------------------------------------------

def test_starting_ability_slug_not_in_kit_or_pool_raises() -> None:
    kit = _kit(abilities=[_ability("shield-bash")])
    with pytest.raises(ValidationError, match="starting_abilities"):
        Playbook(**_valid_playbook(
            starting_kit=kit,
            starting_abilities=["ghost-strike"],  # not in kit or pool
        ))


def test_starting_ability_slug_in_kit_is_valid() -> None:
    kit = _kit(abilities=[_ability("shield-bash")])
    pb = Playbook(**_valid_playbook(
        starting_kit=kit,
        starting_abilities=["shield-bash"],
    ))
    assert "shield-bash" in pb.starting_abilities


def test_starting_ability_slug_in_pool_is_valid() -> None:
    pb = Playbook(**_valid_playbook(
        ability_pool=[_ability("iron-will")],
        starting_abilities=["iron-will"],
    ))
    assert "iron-will" in pb.starting_abilities


# ---------------------------------------------------------------------------
# Cycle 8 — duplicate slugs across kit + pool
# ---------------------------------------------------------------------------

def test_duplicate_ability_slug_across_kit_and_pool_raises() -> None:
    kit = _kit(abilities=[_ability("smite")])
    with pytest.raises(ValidationError):
        Playbook(**_valid_playbook(
            starting_kit=kit,
            ability_pool=[_ability("smite")],  # same slug in both
        ))


def test_duplicate_slug_within_pool_raises() -> None:
    with pytest.raises(ValidationError):
        Playbook(**_valid_playbook(
            ability_pool=[_ability("smite"), _ability("smite")],
        ))


# ---------------------------------------------------------------------------
# PlaybookLibrary — Cycle 9: tracer bullet (loads without error)
# ---------------------------------------------------------------------------

def test_library_loads_and_returns_playbooks() -> None:
    lib = PlaybookLibrary()
    assert len(lib.list()) > 0


# ---------------------------------------------------------------------------
# Cycle 10 — list() returns all four bundled playbooks
# ---------------------------------------------------------------------------

def test_library_list_returns_all_four_playbooks() -> None:
    lib = PlaybookLibrary()
    slugs = {pb.slug for pb in lib.list()}
    assert slugs == {"fighter", "thief", "priest", "artificer"}


# ---------------------------------------------------------------------------
# Cycle 11 — get(slug) returns the correct playbook
# ---------------------------------------------------------------------------

def test_get_fighter_returns_fighter_playbook() -> None:
    lib = PlaybookLibrary()
    pb = lib.get("fighter")
    assert pb.slug == "fighter"
    assert pb.display_name == "Fighter"


# ---------------------------------------------------------------------------
# Cycle 12 — get(unknown slug) raises KeyError
# ---------------------------------------------------------------------------

def test_get_unknown_slug_raises_key_error() -> None:
    lib = PlaybookLibrary()
    with pytest.raises(KeyError):
        lib.get("wizard")


# ---------------------------------------------------------------------------
# Cycle 13 — all four bundled playbooks satisfy schema invariants
# ---------------------------------------------------------------------------

def test_all_bundled_playbooks_have_valid_action_ratings() -> None:
    lib = PlaybookLibrary()
    for pb in lib.list():
        for key, rating in pb.starting_action_ratings.items():
            assert key in {"fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"}
            assert 0 <= rating <= 3, f"{pb.slug}: rating {key}={rating} out of range"


def test_all_bundled_playbooks_have_valid_stress_tracks() -> None:
    lib = PlaybookLibrary()
    for pb in lib.list():
        for track in pb.starting_stress_tracks:
            assert track.track_key in {"body", "composure", "bonds", "weird"}
            assert track.capacity == 4, f"{pb.slug}: capacity {track.capacity} != 4"


def test_all_bundled_playbooks_starting_abilities_resolve() -> None:
    lib = PlaybookLibrary()
    for pb in lib.list():
        available = {a.slug for a in pb.starting_kit.abilities} | {a.slug for a in pb.ability_pool}
        for slug in pb.starting_abilities:
            assert slug in available, f"{pb.slug}: starting_ability {slug!r} not in kit or pool"
