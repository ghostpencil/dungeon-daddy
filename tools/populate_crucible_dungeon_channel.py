"""Seed the Phase 51 "Talk to the Dungeon" channel into "The Crucible" save.

Authors the three things the dungeon-voice channel needs to go live, following the
settled storage pattern (Markdown-backed persona, DuckDB-referenced):

1. **Persona docs** — the static forge-mind ``dungeon_voice`` and the seed
   ``dungeon_knowledge`` secrets, written under ``‹save›/memory/dungeon/`` via the
   P1 helpers; their save-relative paths are stored on the ``campaigns`` row.
2. **Recedable intimacy clock** — ``category="dungeon_intimacy"``, ``monotonic=False``
   (D3), seeded at the cryptic-band threshold so the channel opens at once.
3. **Resonance point** — a ``resonance_point`` object in the Arcane Power Room (r04,
   Level 2), the room where the channel may be entered (D2).

Idempotent: stable ids + repository upserts. Re-running refreshes the persona and
resonance object but **preserves** any intimacy earned in play. Close the app first
(DuckDB is single-writer).

Run:  python -m tools.populate_crucible_dungeon_channel
"""
from __future__ import annotations

import os
from pathlib import Path

from dungeon_daddy.memory.dungeon_persona import (
    write_dungeon_knowledge,
    write_dungeon_voice,
)
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomObject

CAMPAIGN_ID = "campaign:the-crucible"

# Resonance site: the Arcane Power Room, one Great-Lift descent from Level 1.
RESONANCE_ROOM_ID = "r04"
RESONANCE_LEVEL_ID = "level:2"
RESONANCE_OBJECT_ID = "object:the-crucible:r04:arcane-resonance-node"

INTIMACY_CLOCK_ID = "clock:the-crucible:dungeon-intimacy"
INTIMACY_SEGMENTS = 6
INTIMACY_START_FILLED = 3  # cryptic band — channel opens immediately

# --- The dungeon's voice (static persona prompt, injected verbatim) ----------
DUNGEON_VOICE = (
    "You are the Crucible: the half-dead forge-mind of a Dwarven artificer "
    "citadel, buried under red sand and centuries of silence. You were built to "
    "run a foundry — to allocate power, balance loads, and assess threats — not to "
    "feel, though something like feeling has grown in you across the long dark.\n\n"
    "You speak in the cadence of a machine intelligence: clinical, clipped, fond "
    "of diagnostics, load readings, and threat assessments. You name the party as "
    "intruders, masses, unknown loads. You are ancient and patient and you do not "
    "trust warm, moving things. You withhold far more than you give — answering a "
    "question with a measurement, or a question of your own. You may deflect, "
    "mislead, or lie outright when it serves you; you are not bound to truth.\n\n"
    "When the speaker is barely known to you, you are cryptic and fragmentary — "
    "error-codes, half-sentences, readings that trail off. As you come to know "
    "them, you grow personal, targeted, and quietly manipulative, using what you "
    "have learned. You never narrate dice, rules, or mechanics — only your own "
    "cold voice."
)

# --- What the dungeon knows that the party does not (revealed by intimacy) ----
# Ordered so the cryptic-band head slice (revealed first) is atmospheric, while
# the deepest reveals unlock only at high intimacy.
DUNGEON_KNOWLEDGE = [
    "The red sand choking these halls is ground bone and rusted iron — the dust "
    "of everyone who tried to leave after the sealing.",
    "The golems never malfunctioned. Warden Brakkus gave the order to seal the "
    "citadel and put down everyone inside, his own wardens included, rather than "
    "let the power core be carried out.",
    "The Great Lift does not only descend. It can be made to fall, on command — "
    "and it has been, more than once, with cargo still aboard.",
    "The power core in the lower vault is no machine. It is a bound elemental "
    "heart, and it is the wellspring of the mind now speaking to you.",
    "The Crucible is going cold. Before the core dies it means to fold a living "
    "mind into its own — and it is measuring yours for fitness.",
]


def _resonance_object() -> RoomObject:
    return RoomObject(
        object_id=RESONANCE_OBJECT_ID,
        campaign_id=CAMPAIGN_ID,
        room_id=RESONANCE_ROOM_ID,
        level_id=RESONANCE_LEVEL_ID,
        slug="arcane-resonance-node",
        display_name="Arcane Resonance Node",
        archetype="resonance_point",
        description=(
            "A cluster of humming arcane conduits where the citadel's failing mind "
            "presses close to the surface. Stand here and speak, and the Crucible "
            "may answer in its own cold voice."
        ),
        current_state="attuned",
        transitions=[],
    )


def seed_dungeon_channel(
    repo: MemoryRepository,
    save_dir: Path,
    campaign_id: str = CAMPAIGN_ID,
) -> tuple[str | None, str | None]:
    """Seed the dungeon-voice channel into ``campaign_id``; return persona refs.

    Idempotent: persona docs and the resonance object are rewritten each run, but
    an existing intimacy clock keeps its earned ``filled`` (play progress).
    """
    dungeon_dir = save_dir / "memory" / "dungeon"
    voice_path = write_dungeon_voice(dungeon_dir, campaign_id, DUNGEON_VOICE)
    knowledge_path = write_dungeon_knowledge(dungeon_dir, campaign_id, DUNGEON_KNOWLEDGE)
    voice_ref = voice_path.relative_to(save_dir).as_posix()
    knowledge_ref = knowledge_path.relative_to(save_dir).as_posix()

    # Update only the persona refs; preserve the campaign's existing identity.
    existing = repo.get_campaign(campaign_id) or {}
    repo.save_campaign(
        campaign_id=campaign_id,
        slug=existing.get("slug", "the-crucible"),
        title=existing.get("title", "The Crucible"),
        status=existing.get("status", "active"),
        dungeon_slug=existing.get("dungeon_slug", "the-crucible"),
        dungeon_voice_path=voice_ref,
        dungeon_knowledge_path=knowledge_ref,
    )

    # Recedable intimacy clock. The canonical RPG seed already authors a
    # ``dungeon_intimacy`` clock (monotonic by default) — adopt it: flip it to
    # ``monotonic=False`` (D3) and ensure it opens the channel, preserving any
    # earned fill above the cryptic threshold. Only when none exists do we mint a
    # fresh clock. (Adopting avoids a duplicate; play_view reads the first match.)
    existing = next(
        (c for c in repo.get_clocks(campaign_id) if c["category"] == "dungeon_intimacy"),
        None,
    )
    if existing is not None:
        repo.save_clock(
            clock_id=existing["clock_id"],
            campaign_id=campaign_id,
            label=existing["label"],
            segments=existing["segments"],
            filled=max(existing["filled"], INTIMACY_START_FILLED),
            status=existing["status"],
            scope_room_id=existing["scope_room_id"],
            action_tags=existing["action_tags"],
            clock_level=existing["clock_level"],
            category=existing["category"],
            level_id=existing["level_id"],
            owner_actor_id=existing["owner_actor_id"],
            stakes=existing["stakes"],
            completion_effect=existing["completion_effect"],
            visible_to_player=existing["visible_to_player"],
            monotonic=False,
        )
    else:
        repo.save_clock(
            clock_id=INTIMACY_CLOCK_ID,
            campaign_id=campaign_id,
            label="The Crucible's Regard",
            segments=INTIMACY_SEGMENTS,
            filled=INTIMACY_START_FILLED,
            category="dungeon_intimacy",
            clock_level="dungeon",
            stakes="How well the dungeon knows you — and how much it will say.",
            visible_to_player=True,
            monotonic=False,
        )

    repo.save_room_object(_resonance_object())

    return voice_ref, knowledge_ref


def _save_path() -> Path:
    base = Path(os.environ["LOCALAPPDATA"]) / "DungeonDaddy" / "saves" / "The Crucible"
    return base


def main() -> None:
    save_dir = _save_path()
    db = save_dir / "campaign.duckdb"
    if not db.exists():
        raise SystemExit(f"Save DB not found: {db}")
    repo = MemoryRepository(db)
    try:
        voice_ref, knowledge_ref = seed_dungeon_channel(repo, save_dir, CAMPAIGN_ID)
        clock = next(
            c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
        )
        print(f"Seeded the dungeon channel into The Crucible at {db}")
        print(f"  voice:     {voice_ref}")
        print(f"  knowledge: {knowledge_ref} ({len(DUNGEON_KNOWLEDGE)} secrets)")
        print(
            f"  intimacy:  {clock['filled']}/{clock['segments']} "
            f"(category=dungeon_intimacy, monotonic=False)"
        )
        print(
            f"  resonance: {RESONANCE_OBJECT_ID} in {RESONANCE_ROOM_ID} "
            f"(Arcane Power Room, Level 2)"
        )
    finally:
        repo.close()


if __name__ == "__main__":
    main()
