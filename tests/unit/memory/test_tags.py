"""Unit tests for the tag taxonomy validator (Phase 51.8 Slice A1).

Covers T1-T3 of spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md: one namespaced,
colon-delimited controlled vocabulary; `validate_tag` raises on write for
malformed / unknown-namespace tags.
"""

import pytest

from dungeon_daddy.memory.tags import actor_tag, validate_tag


@pytest.mark.parametrize(
    "tag",
    [
        # actor family — all three ratified subtypes
        "actor:pc:mara",
        "actor:npc:elowen",
        "actor:dungeon:golem-a7",
        # ratified / pre-existing simple families
        "location:moonlit-cathedral",
        "location:R1",  # room_ids may be mixed-case (§4.3 validates that separately)
        "level:factory-2",
        "theme:guilt",
        "thread:find-the-vessel",
        "clock:arcane-overload-building",
        "fallout:active",
        "track:weird",
        "emotion:dungeon-curiosity",
        # new families (T2)
        "object:coolant-loop-manifold",
        "item:travel-journal",
        "faction:the-guild",
        "objective:clear-the-gearworks",
        "trait:boss",
    ],
)
def test_canonical_tags_are_accepted_unchanged(tag: str) -> None:
    """T2: every canonical family is valid and returned verbatim."""
    assert validate_tag(tag) == tag


def test_bare_tag_is_invalid() -> None:
    """T1: bare un-namespaced tags (`fighter`, `boss`) are invalid."""
    with pytest.raises(ValueError):
        validate_tag("fighter")


def test_unknown_namespace_is_invalid() -> None:
    """T2: a namespace outside the controlled vocabulary is rejected."""
    with pytest.raises(ValueError):
        validate_tag("bogus:thing")


def test_empty_slug_is_invalid() -> None:
    """T3 (shape): a known namespace with no slug is rejected."""
    with pytest.raises(ValueError):
        validate_tag("theme:")


@pytest.mark.parametrize(
    "tag",
    [
        "actor:protagonist:kira-dawnseeker",  # audit: non-canonical subtype
        "actor:mara",  # audit: two-segment, missing subtype
        "actor:pc:",  # empty slug
    ],
)
def test_actor_requires_canonical_subtype_and_slug(tag: str) -> None:
    """T2: `actor:` is `actor:<pc|npc|dungeon>:<slug>` — nothing else."""
    with pytest.raises(ValueError):
        validate_tag(tag)


@pytest.mark.parametrize(
    ("actor_type", "slug", "expected"),
    [
        ("pc", "kira-dawnseeker", "actor:pc:kira-dawnseeker"),
        ("npc", "wraith-steward", "actor:npc:wraith-steward"),
        # A monster is a non-player creature -> npc subtype (owner ruling
        # 2026-07-10: type-based mapping, actor:dungeon: reserved for the persona).
        ("monster", "golem-a7", "actor:npc:golem-a7"),
        ("dungeon", "the-voice", "actor:dungeon:the-voice"),
        ("dungeon_presence", "factory-spirit", "actor:dungeon:factory-spirit"),
        # A faction actor is a dungeon-side facet -> dungeon subtype.
        ("faction", "desert-djinn-fragment", "actor:dungeon:desert-djinn-fragment"),
    ],
)
def test_actor_tag_maps_actor_type_to_canonical_subtype(
    actor_type: str, slug: str, expected: str
) -> None:
    """§5.1: build the canonical `actor:` tag from an actor record."""
    built = actor_tag(actor_type, slug)
    assert built == expected
    # A builder must never emit an invalid tag.
    assert validate_tag(built) == built


def test_every_actor_type_literal_is_mapped_explicitly() -> None:
    """Drift guard: every ``ActorState.actor_type`` value must be an explicit
    key in the map. The runtime fallback (unknown -> dungeon) exists only as a
    safety net; a new model actor_type must be mapped deliberately, not silently
    classified as the dungeon persona."""
    from typing import get_args

    from dungeon_daddy.memory.tags import _ACTOR_TYPE_TO_SUBTYPE
    from dungeon_daddy.rpg.models import ActorState

    literals = get_args(ActorState.model_fields["actor_type"].annotation)
    assert literals  # sanity: the field really is a Literal
    for actor_type in literals:
        assert actor_type in _ACTOR_TYPE_TO_SUBTYPE, (
            f"actor_type {actor_type!r} is unmapped in _ACTOR_TYPE_TO_SUBTYPE "
            "(map it so actor_tag doesn't silently treat it as the dungeon persona)"
        )
