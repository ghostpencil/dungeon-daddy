from __future__ import annotations

import uuid
from typing import Literal

from dungeon_daddy.rpg.models import ActorState, FalloutRecord, StressTrack
from dungeon_daddy.rpg.stress import mark_stress


def evaluate_fallout(
    actor: ActorState,
    track_key: str,
    campaign_id: str,
    existing_fallout: list[FalloutRecord] | None = None,
) -> tuple[FalloutRecord, StressTrack]:
    existing = existing_fallout or []
    active_on_track = [f for f in existing if f.track_key == track_key and f.status == "active"]
    count = len(active_on_track)
    if count == 0:
        severity = "minor"
    elif count == 1:
        severity = "moderate"
    else:
        severity = "severe"

    title, summary = get_catalog_entry(track_key, severity)
    hooks: dict[str, object] = {}
    if track_key == "weird":
        hooks = {
            "dungeon_influence": True,
            "write_memory": True,
            "dungeon_knowledge_tag": f"actor:{actor.actor_type}:{actor.slug}",
        }

    record = FalloutRecord(
        fallout_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        actor_id=actor.actor_id,
        track_key=track_key,
        severity=severity,
        title=title,
        summary=summary,
        mechanical_hooks=hooks,
    )

    track = actor.stress.get(track_key, StressTrack(track_key=track_key, capacity=4))
    reset_track = track.model_copy(update={"filled": 0})
    return record, reset_track


_CATALOG: dict[tuple[str, str], tuple[str, str]] = {
    ("body", "minor"): (
        "Battered",
        "Bruises and cuts slow you down. Take -1 on physical actions until you rest.",
    ),
    ("body", "moderate"): (
        "Wounded",
        "Something is broken or torn. You cannot push yourself physically without worsening it.",
    ),
    ("body", "severe"): (
        "Broken",
        "You are seriously injured. Someone must carry you, or you fall behind permanently.",
    ),
    ("composure", "minor"): (
        "Rattled",
        "Fear lingers at the edge of your thoughts. The next tense moment costs you extra.",
    ),
    ("composure", "moderate"): (
        "Shaken",
        "You flinch at shadows. Focused actions require an extra effort of will.",
    ),
    ("composure", "severe"): (
        "Broken Down",
        "You can barely hold yourself together. Others must support you or you freeze.",
    ),
    ("bonds", "minor"): (
        "Distant",
        "You have pulled away from someone close. Trust requires deliberate repair.",
    ),
    ("bonds", "moderate"): (
        "Fractured",
        "A relationship has cracked under pressure. Someone doubts you or you doubt them.",
    ),
    ("bonds", "severe"): (
        "Severed",
        "A bond has broken entirely. Reunion will require more than words.",
    ),
    ("weird", "minor"): (
        "Touched",
        "The dungeon has brushed against your mind. You dream in its geometry.",
    ),
    ("weird", "moderate"): (
        "Marked",
        "The dungeon knows your shape. It can find the seams in you and press there.",
    ),
    ("weird", "severe"): (
        "Claimed",
        "Part of you belongs to the dungeon now. It speaks through your silence.",
    ),
}


_INTIMACY_COST_TAGS: dict[str, list[str]] = {
    "comfort": ["vulnerability:solace", "dungeon:bond"],
    "healing": ["vulnerability:dependency", "dungeon:bond"],
    "guidance": ["vulnerability:trust", "dungeon:leverage"],
    "refuge": ["vulnerability:shelter", "dungeon:bond"],
    "visions": ["vulnerability:insight", "dungeon:leverage"],
}


def apply_intimacy_risk(
    actor: ActorState,
    benefit_type: Literal["comfort", "healing", "guidance", "refuge", "visions"],
    campaign_id: str,
) -> tuple[StressTrack, list[str]]:
    weird_track = actor.stress.get(
        "weird", StressTrack(track_key="weird", capacity=4)
    )
    updated_weird = mark_stress(weird_track, amount=1)
    cost_tags = list(_INTIMACY_COST_TAGS.get(benefit_type, ["dungeon:bond"]))
    return updated_weird, cost_tags


def get_catalog_entry(track_key: str, severity: str) -> tuple[str, str]:
    return _CATALOG[(track_key, severity)]
