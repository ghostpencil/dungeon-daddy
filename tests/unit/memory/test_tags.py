"""Unit tests for the tag taxonomy validator (Phase 51.8 Slice A1).

Covers T1-T3 of spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md: one namespaced,
colon-delimited controlled vocabulary; `validate_tag` raises on write for
malformed / unknown-namespace tags.
"""

import pytest

from dungeon_daddy.memory.tags import validate_tag


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
