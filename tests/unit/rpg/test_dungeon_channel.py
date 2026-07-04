from dungeon_daddy.rpg.dungeon_channel import (
    REASON_NOT_HERE,
    REASON_NOT_INTIMATE,
    active_objective,
    dungeon_channel_available,
    dungeon_systems_status,
    located_systems_status,
    object_location,
    reveal_knowledge,
    unlocked_knowledge,
)
from dungeon_daddy.rpg.models import ClockState


def _located_obj(slug, name, archetype, state, room_id):
    return {
        "slug": slug,
        "display_name": name,
        "archetype": archetype,
        "current_state": state,
        "room_id": room_id,
    }


_ROOM_LABELS = {"r02": "Level 2 — Central Hub", "R4": "Level 1 — Elevator Shaft"}


def test_located_systems_status_appends_location_for_subsystems():
    objs = [
        _located_obj("coolant-loop", "Coolant Loop Manifold", "structure", "ruptured", "r02"),
        _located_obj("great-lift", "The Great Lift", "mechanism", "powered", "R4"),
        _located_obj("crate", "Cargo Crate", "container", "sealed", "r02"),  # not a subsystem
    ]
    assert located_systems_status(objs, _ROOM_LABELS) == [
        ("Coolant Loop Manifold", "ruptured", "Level 2 — Central Hub"),
        ("The Great Lift", "powered", "Level 1 — Elevator Shaft"),
    ]


def test_located_systems_status_blank_location_when_room_unknown():
    objs = [_located_obj("x", "Mystery Engine", "mechanism", "idle", "r99")]
    assert located_systems_status(objs, _ROOM_LABELS) == [("Mystery Engine", "idle", "")]


def test_object_location_resolves_target_slug_to_room_label():
    objs = [_located_obj("coolant-loop", "Coolant Loop Manifold", "structure", "ruptured", "r02")]
    assert object_location("coolant-loop", objs, _ROOM_LABELS) == "Level 2 — Central Hub"


def test_object_location_none_when_slug_absent():
    objs = [_located_obj("coolant-loop", "Coolant Loop Manifold", "structure", "ruptured", "r02")]
    assert object_location("missing", objs, _ROOM_LABELS) is None


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


def test_open_at_tier_zero_with_latching_clock() -> None:
    # Phase 51.5 D6: the intimacy clock is a latching tier index (segments=#tiers,
    # filled=#completed). The channel opens cryptic at tier 0 (filled=0) — intimacy
    # gates *content* (per-tier knowledge), not access.
    available, reason = dungeon_channel_available(
        _room(True), _intimacy(segments=4, filled=0, monotonic=True)
    )
    assert available is True
    assert reason is None


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


# --- tier knowledge / active objective (Slice 7) --------------------------


def _objective(
    *,
    slug: str,
    tier_index: int,
    status: str,
    reveals_knowledge: list[str] | None = None,
    description: str = "",
) -> dict:
    # The repo dict shape (get_objectives), ordered by tier_index, slug.
    return {
        "objective_id": f"obj-{slug}",
        "campaign_id": "c1",
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "description": description,
        "tier_index": tier_index,
        "status": status,
        "completion": {"kind": "object_state", "target_slug": slug, "required_state": "restored"},
        "advances_clock_slug": "dungeon_intimacy",
        "reveals_knowledge": reveals_knowledge or [],
    }


def test_unlocked_knowledge_unions_completed_tiers() -> None:
    objectives = [
        _objective(slug="coolant", tier_index=0, status="completed",
                   reveals_knowledge=["secret-a", "secret-b"]),
        _objective(slug="reactor", tier_index=1, status="completed",
                   reveals_knowledge=["secret-c"]),
    ]
    assert unlocked_knowledge(objectives) == ["secret-a", "secret-b", "secret-c"]


def test_unlocked_knowledge_excludes_locked_and_active() -> None:
    objectives = [
        _objective(slug="coolant", tier_index=0, status="completed",
                   reveals_knowledge=["known"]),
        _objective(slug="reactor", tier_index=1, status="active",
                   reveals_knowledge=["not-yet"]),
        _objective(slug="vault", tier_index=2, status="locked",
                   reveals_knowledge=["hidden"]),
    ]
    assert unlocked_knowledge(objectives) == ["known"]


def test_unlocked_knowledge_preserves_tier_order_and_dedupes() -> None:
    objectives = [
        _objective(slug="coolant", tier_index=0, status="completed",
                   reveals_knowledge=["shared", "first"]),
        _objective(slug="reactor", tier_index=1, status="completed",
                   reveals_knowledge=["second", "shared"]),
    ]
    assert unlocked_knowledge(objectives) == ["shared", "first", "second"]


def test_unlocked_knowledge_empty_when_nothing_completed() -> None:
    objectives = [
        _objective(slug="coolant", tier_index=0, status="active",
                   reveals_knowledge=["nope"]),
    ]
    assert unlocked_knowledge(objectives) == []


def test_active_objective_returns_the_active_one() -> None:
    objectives = [
        _objective(slug="coolant", tier_index=0, status="completed"),
        _objective(slug="reactor", tier_index=1, status="active",
                   description="Restore the arc reactor."),
        _objective(slug="vault", tier_index=2, status="locked"),
    ]
    found = active_objective(objectives)
    assert found is not None
    assert found["slug"] == "reactor"
    assert found["description"] == "Restore the arc reactor."


def test_active_objective_none_when_no_active() -> None:
    objectives = [
        _objective(slug="coolant", tier_index=0, status="completed"),
        _objective(slug="reactor", tier_index=1, status="locked"),
    ]
    assert active_objective(objectives) is None


def test_active_objective_returns_first_when_multiple_active() -> None:
    # The ladder activates one tier at a time, but be deterministic regardless.
    objectives = [
        _objective(slug="coolant", tier_index=0, status="active"),
        _objective(slug="reactor", tier_index=1, status="active"),
    ]
    found = active_objective(objectives)
    assert found is not None
    assert found["slug"] == "coolant"
