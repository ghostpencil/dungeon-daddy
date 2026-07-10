"""Tag taxonomy validation (Phase 51.8 Slice A1).

One namespaced, colon-delimited controlled vocabulary for the descriptive
`tags` field of every world entity (T1-T3 of
`spec/TAG_TAXONOMY_AND_NARRATOR_LOOKUP.md`). Bare un-namespaced tags are
invalid. `validate_tag` is called by repo save paths (raises on write);
reads stay permissive so old saves still load.
"""

from __future__ import annotations

# T2: the canonical namespace families (spec §2). Every valid tag begins with
# one of these, followed by ``:`` and at least one non-empty segment.
TAG_NAMESPACES: frozenset[str] = frozenset(
    {
        "actor",  # special: actor:<subtype>:<slug> (see ACTOR_SUBTYPES)
        "location",
        "level",
        "theme",
        "thread",
        "clock",
        "object",
        "item",
        "faction",
        "objective",
        "trait",
        "fallout",
        "track",
        "emotion",
    }
)

# The `actor:` family is three-segment: actor:<subtype>:<slug>. Only these
# subtypes are canonical (T2 / T6 fold `protagonist` -> `pc`).
ACTOR_SUBTYPES: frozenset[str] = frozenset({"pc", "npc", "dungeon"})

# Map a persisted ``ActorState.actor_type`` to its canonical `actor:` subtype
# (owner ruling 2026-07-10, §5.1): players -> ``pc``; non-player creatures
# (``npc``/``monster``) -> ``npc``; the dungeon persona and its facets
# (``dungeon``/``dungeon_presence``/``faction``) -> ``dungeon``. Any unknown
# type falls back to ``dungeon`` so the builder is total and never raises.
_ACTOR_TYPE_TO_SUBTYPE: dict[str, str] = {
    "pc": "pc",
    "npc": "npc",
    "monster": "npc",
    "dungeon": "dungeon",
    "dungeon_presence": "dungeon",
    "faction": "dungeon",
}


def actor_tag(actor_type: str, slug: str) -> str:
    """Build the canonical ``actor:<subtype>:<slug>`` tag for an actor record.

    The subtype is derived from ``actor_type`` per :data:`_ACTOR_TYPE_TO_SUBTYPE`
    so retrieval filters match the canonical tags on memories. The result is
    guaranteed to satisfy :func:`validate_tag`.
    """
    subtype = _ACTOR_TYPE_TO_SUBTYPE.get(actor_type, "dungeon")
    return f"actor:{subtype}:{slug}"


def validate_tag(tag: str) -> str:
    """Validate a single tag against the taxonomy; return it unchanged.

    Raises ``ValueError`` for a bare (un-namespaced) tag, a tag whose
    namespace is outside :data:`TAG_NAMESPACES`, an `actor:` tag that is not
    `actor:<pc|npc|dungeon>:<slug>`, or any tag missing its slug.
    """
    namespace, sep, rest = tag.partition(":")
    if not sep:
        raise ValueError(f"tag is not namespaced: {tag!r}")
    if namespace not in TAG_NAMESPACES:
        raise ValueError(f"unknown tag namespace {namespace!r}: {tag!r}")
    if namespace == "actor":
        subtype, subsep, slug = rest.partition(":")
        if not subsep or subtype not in ACTOR_SUBTYPES or not slug:
            raise ValueError(
                f"actor tag must be actor:<pc|npc|dungeon>:<slug>: {tag!r}"
            )
        return tag
    if not rest:
        raise ValueError(f"tag has no slug: {tag!r}")
    return tag
