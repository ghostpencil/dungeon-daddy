from __future__ import annotations

import math

from dungeon_daddy.rpg.models import ClockState

# Tunable intimacy gate threshold, as a fraction of the clock's segments filled.
# Open balance question — see spec/PHASE_51_TALK_TO_THE_DUNGEON.md §6 and
# BALANCE_NOTES.md when tuning the band boundaries.
INTIMACY_THRESHOLD = 0.5

# Fraction of the latching tier-index clock that must be filled for the channel
# to open *at all* (Phase 51.5 D6 / §4.3.3, resolves the §6 open question). Zero
# so the channel opens cryptic at tier 0 (filled=0); the *tiers* gate content
# (per-tier knowledge), not access. Kept separate from INTIMACY_THRESHOLD, which
# still bands the deprecated flat reveal_knowledge path.
CHANNEL_OPEN_THRESHOLD = 0.0

# Knowledge-revelation banding (spec §4.5; tunable — see §6 / BALANCE_NOTES.md).
# At/above HIGH_INTIMACY_THRESHOLD the dungeon draws on its full knowledge;
# in the cryptic band [INTIMACY_THRESHOLD, HIGH_INTIMACY_THRESHOLD) it reveals
# only a head fragment — CRYPTIC_REVEAL_FRACTION of the list (at least one item).
HIGH_INTIMACY_THRESHOLD = 0.85
CRYPTIC_REVEAL_FRACTION = 0.5

# Lock reasons surfaced to the player when the channel is closed.
REASON_NOT_HERE = "You are not standing where the dungeon can hear you."
REASON_NOT_INTIMATE = "The dungeon does not yet know you well enough to speak."

# Object archetypes the dungeon models as restorable *subsystems* (spec §4.2).
SUBSYSTEM_ARCHETYPES = ("mechanism", "structure")


def dungeon_systems_status(room_objects: list[dict]) -> list[tuple[str, str]]:
    """Return a deterministic snapshot of the dungeon's subsystems (spec §4.2).

    ``room_objects`` are repo dicts (the ``get_objects_for_campaign`` shape, each
    with ``display_name``/``archetype``/``current_state``). Only subsystem-tagged
    objects (archetype ``mechanism``/``structure``) are reported, as
    ``(display_name, current_state)`` pairs, in input order — so the dungeon can
    give a *truthful* systems assessment.
    """
    return [
        (obj["display_name"], obj["current_state"])
        for obj in room_objects
        if obj.get("archetype") in SUBSYSTEM_ARCHETYPES
    ]


def unlocked_knowledge(objectives: list[dict]) -> list[str]:
    """Return the secrets the dungeon may draw on now (spec §4.3.4 / D7).

    ``objectives`` are repo dicts (the ``get_objectives`` shape, ordered by
    ``tier_index, slug``). The unlocked knowledge at the current tier is the
    union of ``reveals_knowledge`` across all **completed** objectives, in tier
    order, de-duplicated (first occurrence wins). Locked/active tiers contribute
    nothing — their secrets are still gated.
    """
    unlocked: list[str] = []
    for obj in objectives:
        if obj.get("status") != "completed":
            continue
        for secret in obj.get("reveals_knowledge", []):
            if secret not in unlocked:
                unlocked.append(secret)
    return unlocked


def active_objective(objectives: list[dict]) -> dict | None:
    """Return the active objective — the dungeon's "what I want next" (spec §4.3.4).

    ``objectives`` are repo dicts (the ``get_objectives`` shape, ordered by
    ``tier_index, slug``). The ladder activates one tier at a time, so the first
    objective whose ``status`` is ``active`` is the dangled next objective; its
    ``description`` is fed to the dungeon as the next-objective hint. Returns
    ``None`` when no objective is active.
    """
    for obj in objectives:
        if obj.get("status") == "active":
            return obj
    return None


def dungeon_channel_available(
    room_context: dict,
    intimacy_clock: ClockState | None,
) -> tuple[bool, str | None]:
    """Decide whether the freeform dungeon-voice channel may open.

    Two gates, both required (spec §2 / §4.3):
      * **Location** — the current room is a resonance point.
      * **Intimacy** — a non-monotonic intimacy clock is at/above threshold,
        read **live** from ``filled``/``segments`` (never a completion event).

    Returns ``(True, None)`` when open, else ``(False, reason)`` where reason is
    the not-here vs. not-intimate-enough lock message.
    """
    if not room_context.get("resonance_point"):
        return (False, REASON_NOT_HERE)
    if intimacy_clock is None or intimacy_clock.segments <= 0:
        return (False, REASON_NOT_INTIMATE)
    if intimacy_clock.filled / intimacy_clock.segments < CHANNEL_OPEN_THRESHOLD:
        return (False, REASON_NOT_INTIMATE)
    return (True, None)


def reveal_knowledge(knowledge: list[str], filled: int, segments: int) -> list[str]:
    """Return the slice of ``dungeon_knowledge`` the dungeon may draw on now.

    Banding by intimacy fraction ``filled / segments`` (spec §4.5):
      * below ``INTIMACY_THRESHOLD`` → nothing (the dungeon stays silent);
      * in the cryptic band → a fragmentary head slice;
      * at/above ``HIGH_INTIMACY_THRESHOLD`` → the full list.
    """
    if segments <= 0:
        return []
    ratio = filled / segments
    if ratio < INTIMACY_THRESHOLD:
        return []
    if ratio >= HIGH_INTIMACY_THRESHOLD:
        return list(knowledge)
    count = max(1, math.ceil(len(knowledge) * CRYPTIC_REVEAL_FRACTION))
    return list(knowledge[:count])
