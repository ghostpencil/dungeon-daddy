"""Deterministic stress-track selection — Phase 35.6."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from dungeon_daddy.rpg.models import ClockState

StressTrackKey = Literal["body", "composure", "bonds", "weird"]

_ACTION_TO_STRESS: dict[str, StressTrackKey] = {
    "fight": "body",
    "move": "body",
    "endure": "body",
    "tinker": "body",
    "study": "composure",
    "focus": "composure",
    "sense": "composure",
    "sway": "bonds",
    "channel": "weird",
}

_CLOCK_CATEGORY_TO_STRESS: dict[str, StressTrackKey] = {
    "danger": "body",
    "hazard": "body",
    "pursuit": "body",
    "boss": "body",
    "escape": "body",
    "horror": "composure",
    "fear": "composure",
    "dread": "composure",
    "despair": "composure",
    "panic": "composure",
    "relationship": "bonds",
    "betrayal": "bonds",
    "dependency": "bonds",
    "isolation": "bonds",
    "faction_pressure": "bonds",
    "ritual": "weird",
    "occult": "weird",
    "magic": "weird",
    "dungeon_intimacy": "weird",
    "allure": "weird",
    "memory_bleed": "weird",
    "transformation": "weird",
}

_CLOCK_LEVEL_TO_STRESS: dict[str, StressTrackKey] = {
    "room": "body",
    "level": "body",
    "dungeon": "weird",
    "quest": "composure",
    "character": "bonds",
    "faction": "bonds",
}

_BODY_KEYWORDS: frozenset[str] = frozenset({
    "attack", "fight", "strike", "hit", "block", "run", "jump", "climb",
    "dodge", "force", "break", "lift", "push", "carry", "poison", "wound",
    "pain", "blood", "trap", "fire", "steam", "acid", "fall",
})
_COMPOSURE_KEYWORDS: frozenset[str] = frozenset({
    "fear", "panic", "terror", "horror", "shame", "guilt", "grief",
    "despair", "nightmare", "memory", "regret", "truth", "confess",
    "focus", "calm", "resist",
})
_BONDS_KEYWORDS: frozenset[str] = frozenset({
    "trust", "betray", "comfort", "reject", "abandon", "protect", "promise",
    "friend", "ally", "love", "dependency", "help", "isolate", "relationship",
    "forgive", "convince", "deceive",
})
_WEIRD_KEYWORDS: frozenset[str] = frozenset({
    "dungeon", "vision", "ritual", "magic", "spell", "spirit", "ghost",
    "dream", "voice", "whisper", "allure", "intimacy", "claim",
    "absorb", "transform", "channel", "entity", "alien",
})


def _from_intent(intent: str) -> StressTrackKey | None:
    words = set(intent.lower().split())
    if words & _WEIRD_KEYWORDS:
        return "weird"
    if words & _BONDS_KEYWORDS:
        return "bonds"
    if words & _COMPOSURE_KEYWORDS:
        return "composure"
    if words & _BODY_KEYWORDS:
        return "body"
    return None


def choose_stress_track(
    *,
    action_key: str,
    intent: str | None = None,
    matched_clocks: "list[ClockState] | None" = None,
    explicit_track: StressTrackKey | None = None,
) -> StressTrackKey:
    if explicit_track is not None:
        return explicit_track

    for clock in matched_clocks or []:
        if clock.category and clock.category in _CLOCK_CATEGORY_TO_STRESS:
            return _CLOCK_CATEGORY_TO_STRESS[clock.category]

    for clock in matched_clocks or []:
        if clock.clock_level in _CLOCK_LEVEL_TO_STRESS:
            return _CLOCK_LEVEL_TO_STRESS[clock.clock_level]

    if intent:
        from_kw = _from_intent(intent)
        if from_kw is not None:
            return from_kw

    from_action = _ACTION_TO_STRESS.get(action_key)
    if from_action is not None:
        return from_action

    return "body"
