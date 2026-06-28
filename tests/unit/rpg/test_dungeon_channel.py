from dungeon_daddy.rpg.dungeon_channel import (
    REASON_NOT_HERE,
    REASON_NOT_INTIMATE,
    dungeon_channel_available,
    dungeon_systems_status,
    reveal_knowledge,
)
from dungeon_daddy.rpg.models import ClockState


def _intimacy(**kwargs) -> ClockState:  # type: ignore[no-untyped-def]
    defaults = dict(
        clock_id="intimacy",
        campaign_id="c1",
        label="The Dungeon Knows You",
        segments=6,
        filled=3,
        category="dungeon_intimacy",
        clock_level="dungeon",
        monotonic=False,
    )
    defaults.update(kwargs)
    return ClockState(**defaults)


def _room(resonance_point: bool) -> dict:
    return {"room_id": "R1", "resonance_point": resonance_point}


def test_open_when_resonance_and_intimacy_at_threshold() -> None:
    available, reason = dungeon_channel_available(_room(True), _intimacy(filled=3))
    assert available is True
    assert reason is None


def test_closed_when_not_a_resonance_point() -> None:
    available, reason = dungeon_channel_available(_room(False), _intimacy(filled=6))
    assert available is False
    assert reason == REASON_NOT_HERE


def test_closed_when_intimacy_below_threshold() -> None:
    available, reason = dungeon_channel_available(_room(True), _intimacy(filled=2))
    assert available is False
    assert reason == REASON_NOT_INTIMATE


def test_closed_when_intimacy_clock_absent() -> None:
    available, reason = dungeon_channel_available(_room(True), None)
    assert available is False
    assert reason == REASON_NOT_INTIMATE


def test_open_at_exact_threshold_boundary() -> None:
    # 3/6 == 0.5 == INTIMACY_THRESHOLD — at threshold counts as open (>=).
    available, _ = dungeon_channel_available(_room(True), _intimacy(segments=6, filled=3))
    assert available is True


def test_not_here_takes_precedence_when_both_gates_fail() -> None:
    available, reason = dungeon_channel_available(_room(False), None)
    assert available is False
    assert reason == REASON_NOT_HERE


# --- reveal_knowledge (Slice 5) -------------------------------------------

_KNOWLEDGE = ["secret-1", "secret-2", "secret-3", "secret-4"]


def test_reveal_none_below_intimacy_threshold() -> None:
    # 2/6 ≈ 0.33 < INTIMACY_THRESHOLD (0.5) → the dungeon reveals nothing.
    assert reveal_knowledge(_KNOWLEDGE, filled=2, segments=6) == []


def test_reveal_full_list_at_high_fill() -> None:
    # 6/6 == 1.0 ≥ HIGH_INTIMACY_THRESHOLD → the dungeon draws on everything.
    assert reveal_knowledge(_KNOWLEDGE, filled=6, segments=6) == _KNOWLEDGE


def test_reveal_fragmentary_head_slice_in_cryptic_band() -> None:
    # 3/6 == 0.5 — at threshold but below high fill → only a head fragment,
    # CRYPTIC_REVEAL_FRACTION (0.5) of 4 == the first 2 secrets, in order.
    assert reveal_knowledge(_KNOWLEDGE, filled=3, segments=6) == _KNOWLEDGE[:2]


def test_reveal_empty_knowledge_returns_empty() -> None:
    # Nothing to reveal even at full intimacy.
    assert reveal_knowledge([], filled=6, segments=6) == []


def test_reveal_guards_zero_segments() -> None:
    # No divide-by-zero; an unsized clock reveals nothing.
    assert reveal_knowledge(_KNOWLEDGE, filled=0, segments=0) == []


def test_reveal_cryptic_band_yields_at_least_one_fragment() -> None:
    # A single-secret list in the cryptic band still surfaces that one fragment.
    assert reveal_knowledge(["only-secret"], filled=3, segments=6) == ["only-secret"]


def test_reveal_full_list_at_exact_high_threshold_boundary() -> None:
    # 17/20 == 0.85 == HIGH_INTIMACY_THRESHOLD — at the boundary counts as high (>=).
    assert reveal_knowledge(_KNOWLEDGE, filled=17, segments=20) == _KNOWLEDGE


# --- dungeon_systems_status (Slice 6) -------------------------------------


def _obj(archetype: str, display_name: str, current_state: str) -> dict:
    # The repo dict shape (get_objects_for_campaign / get_objects_by_room).
    return {
        "object_id": f"o-{display_name}",
        "slug": display_name.lower().replace(" ", "-"),
        "display_name": display_name,
        "archetype": archetype,
        "current_state": current_state,
    }


def test_systems_status_reports_subsystem_name_and_state() -> None:
    objs = [_obj("mechanism", "Coolant Loop", "offline")]
    assert dungeon_systems_status(objs) == [("Coolant Loop", "offline")]


def test_systems_status_excludes_non_subsystem_archetypes() -> None:
    # Doors, containers, resonance points etc. are not subsystems.
    objs = [
        _obj("door", "North Gate", "locked"),
        _obj("structure", "Support Pillar", "damaged"),
        _obj("resonance_point", "Resonance Node", "active"),
        _obj("container", "Supply Crate", "closed"),
    ]
    assert dungeon_systems_status(objs) == [("Support Pillar", "damaged")]


def test_systems_status_preserves_input_order() -> None:
    # The caller orders room_objects (e.g. repo by slug); the helper is faithful.
    objs = [
        _obj("mechanism", "Coolant Loop", "offline"),
        _obj("door", "Blast Door", "sealed"),
        _obj("structure", "Forge Vault", "restored"),
        _obj("mechanism", "Arc Reactor", "online"),
    ]
    assert dungeon_systems_status(objs) == [
        ("Coolant Loop", "offline"),
        ("Forge Vault", "restored"),
        ("Arc Reactor", "online"),
    ]


def test_systems_status_empty_input_returns_empty() -> None:
    assert dungeon_systems_status([]) == []
