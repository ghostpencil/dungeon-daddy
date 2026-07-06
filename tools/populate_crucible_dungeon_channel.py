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
from dataclasses import dataclass
from pathlib import Path

from dungeon_daddy.memory.dungeon_persona import (
    write_dungeon_knowledge,
    write_dungeon_voice,
)
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import (
    Objective,
    ObjectiveCompletion,
    ObjectReactionBinding,
    ObjectTransition,
    RoomObject,
)

CAMPAIGN_ID = "campaign:the-crucible"

# Resonance site: the Arcane Power Room, one Great-Lift descent from Level 1.
RESONANCE_ROOM_ID = "r04"
RESONANCE_LEVEL_ID = "level:2"
RESONANCE_OBJECT_ID = "object:the-crucible:r04:arcane-resonance-node"

INTIMACY_CLOCK_ID = "clock:the-crucible:dungeon-intimacy"
# Phase 51.5 D6: the intimacy clock is now a latching tier index —
# ``segments`` = number of ladder tiers, ``filled`` = number of completed
# objectives. (Reverts the Phase 51 ``monotonic=False`` wide-open hack.)
INTIMACY_SEGMENTS = 4
INTIMACY_CATEGORY = "dungeon_intimacy"

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


# --- The intimacy ladder (Phase 51.5 D3) -------------------------------------
# Four tiers climbed by *doing*: restoring a dungeon subsystem completes that
# tier's objective, which (via the objective service, the single intimacy-tick
# source — D5) advances the latching clock one tier and unlocks the tier's
# secrets. Tier 0 **adopts** the Crucible's existing Sand-Choked Gearworks; tiers
# 1-3 are fresh subsystems authored across Level 2, near the resonance node.


@dataclass(frozen=True)
class _Rung:
    """One tier of the ladder: a subsystem to restore + the objective that tracks it."""

    tier: int
    objective_slug: str
    title: str
    description: str  # the dungeon's "what I want next" hint (machine voice)
    subsystem_slug: str
    required_state: str
    reveals_knowledge: list[str]
    # Class-flavored, contested approaches that all converge on ``required_state``
    # (Phase 51.5 Part A Slice 4). Each verb is one of the nine core action
    # ratings so an actor can attempt it; thematic per obstacle. Empty for tier 0
    # (its approaches are authored on the adopted gearworks by the Level-1 seed).
    approaches: tuple[str, ...] = ()
    # Fresh subsystems authored by this seed (tier 0 adopts an existing object,
    # so its subsystem fields are None — we never re-author/clobber it).
    room_id: str | None = None
    level_id: str | None = None
    display_name: str | None = None
    archetype: str | None = None
    broken_state: str | None = None
    broken_description: str | None = None
    # Phase 51.6 World Reaction Policy (§6): the subsystem obstacles are `scripted`
    # — success completes the objective (intimacy via the service, D5); a miss
    # misfires arcane power into the dungeon-level Overload clock (§5), never a
    # fan-out across unrelated clocks. Tier 0 (no subsystem here) is authored on
    # the adopted gearworks by the Level-1 seed.
    miss_clock_slug: str | None = None
    miss_clock_delta: int = 0


LADDER: list[_Rung] = [
    _Rung(
        tier=0,
        objective_slug="clear-the-gearworks",
        title="Clear the Sand-Choked Gearworks",
        description=(
            "Primary intake is fouled. Clear the sand-choked gearworks in the "
            "assembly hall above; I cannot draw breath until the works turn."
        ),
        subsystem_slug="gearworks",  # adopts the existing R4 structure
        required_state="cleared",
        reveals_knowledge=[
            "The red sand choking these halls is ground bone and rusted iron — the "
            "dust of everyone who tried to leave after the sealing."
        ],
    ),
    _Rung(
        tier=1,
        objective_slug="restore-the-coolant-loop",
        title="Restore the Coolant Loop",
        description=(
            "Thermal margin is failing. Seal the ruptured coolant loop near the "
            "node, or I will burn through what little of myself remains."
        ),
        subsystem_slug="coolant-loop",
        required_state="restored",
        # Delicate arcane piping — sealed by precise work or re-fluxed with power,
        # never brute-forced (that would only burst it further).
        approaches=("tinker", "channel"),
        reveals_knowledge=[
            "The golems never malfunctioned. Warden Brakkus gave the order to seal "
            "the citadel and put down everyone inside, his own wardens included, "
            "rather than let the power core be carried out."
        ],
        room_id="r02",
        level_id=RESONANCE_LEVEL_ID,
        display_name="Coolant Loop Manifold",
        archetype="structure",
        broken_state="ruptured",
        broken_description=(
            "A burst ring of arcane coolant piping, weeping frost and steam. "
            "Resealed, it would carry the dungeon's heat away once more."
        ),
        miss_clock_slug="arcane-overload-building",
        miss_clock_delta=1,
    ),
    _Rung(
        tier=2,
        objective_slug="recharge-the-arcane-conduits",
        title="Recharge the Arcane Conduits",
        description=(
            "Half my pathways are dark. Recharge the dormant arcane conduits and "
            "I will open more of myself to you."
        ),
        subsystem_slug="arcane-conduits",
        required_state="charged",
        # An arcane/lore obstacle — pour power in, decipher the rune-lattice, or
        # physically reconnect the conduits.
        approaches=("channel", "study", "tinker"),
        reveals_knowledge=[
            "The Great Lift does not only descend. It can be made to fall, on "
            "command — and it has been, more than once, with cargo still aboard."
        ],
        room_id="r03",
        level_id=RESONANCE_LEVEL_ID,
        display_name="Arcane Conduit Array",
        archetype="mechanism",
        broken_state="dormant",
        broken_description=(
            "A lattice of cold arcane conduits, their runes faded to grey. "
            "Recharged, they would carry power back into the citadel's mind."
        ),
        miss_clock_slug="arcane-overload-building",
        miss_clock_delta=1,
    ),
    _Rung(
        tier=3,
        objective_slug="stabilize-the-core-containment",
        title="Stabilize the Core Containment",
        description=(
            "The heart of me is slipping its bindings. Stabilize the core "
            "containment in the deep vault, and you will know what I am."
        ),
        subsystem_slug="core-containment",
        required_state="stabilized",
        # The climactic failing ward — reinforce it with power, hold it steady
        # through focus, or brace the guttering ring by main strength.
        approaches=("channel", "focus", "endure"),
        reveals_knowledge=[
            "The power core in the lower vault is no machine. It is a bound "
            "elemental heart, and it is the wellspring of the mind now speaking "
            "to you.",
            "The Crucible is going cold. Before the core dies it means to fold a "
            "living mind into its own — and it is measuring yours for fitness.",
        ],
        room_id="r05",
        level_id=RESONANCE_LEVEL_ID,
        display_name="Core Containment Ring",
        archetype="structure",
        broken_state="failing",
        broken_description=(
            "The containment ring around the dungeon's bound heart, its wards "
            "guttering. Stabilized, it would hold the core together a while longer."
        ),
        # Climax subsystem — a slip here is dangerous: +2 on the Overload clock.
        miss_clock_slug="arcane-overload-building",
        miss_clock_delta=2,
    ),
]


def _objective_id(rung: _Rung) -> str:
    return f"objective:the-crucible:{rung.objective_slug}"


def _subsystem_object(rung: _Rung) -> RoomObject:
    """The fresh subsystem RoomObject for a tier (tiers 1-3 only).

    The subsystem is an *obstacle*: one contested transition per class-flavored
    approach, all from ``broken_state`` to ``required_state`` (the convergence
    that lets any path complete the objective the same way — Part A Slice 4).
    """
    assert rung.room_id and rung.level_id and rung.archetype and rung.broken_state
    assert rung.approaches, f"tier {rung.tier} subsystem needs contested approaches"
    object_id = f"object:the-crucible:{rung.room_id}:{rung.subsystem_slug}"
    # Phase 51.6 §6: `scripted` control — a miss ticks one authored adverse clock,
    # never the intimacy/objective/relationship/faction clocks (firewall, §3).
    bindings: list[ObjectReactionBinding] = []
    if rung.miss_clock_slug is not None:
        bindings.append(
            ObjectReactionBinding(
                binding_id=f"{object_id}:miss",
                object_id=object_id,
                action_verb="*",
                outcome="miss",
                clock_slug=rung.miss_clock_slug,
                clock_delta=rung.miss_clock_delta,
            )
        )
    return RoomObject(
        object_id=object_id,
        campaign_id=CAMPAIGN_ID,
        room_id=rung.room_id,
        level_id=rung.level_id,
        slug=rung.subsystem_slug,
        display_name=rung.display_name or rung.subsystem_slug,
        archetype=rung.archetype,
        description=rung.broken_description or "",
        current_state=rung.broken_state,
        transitions=[
            ObjectTransition(
                transition_id=f"{object_id}:{verb}",
                object_id=object_id,
                from_state=rung.broken_state,
                to_state=rung.required_state,
                trigger=verb,
                contested=True,
                action_verb=verb,
                advances_clock_slug=None,  # D5: the objective service ticks intimacy
            )
            for verb in rung.approaches
        ],
        reaction_policy="scripted" if bindings else "ambient",
        reaction_bindings=bindings,
    )


def _objective(rung: _Rung, status: str) -> Objective:
    return Objective(
        objective_id=_objective_id(rung),
        campaign_id=CAMPAIGN_ID,
        slug=rung.objective_slug,
        title=rung.title,
        description=rung.description,
        tier_index=rung.tier,
        status=status,
        completion=ObjectiveCompletion(
            kind="object_state",
            target_slug=rung.subsystem_slug,
            required_state=rung.required_state,
        ),
        advances_clock_slug=INTIMACY_CATEGORY,
        reveals_knowledge=list(rung.reveals_knowledge),
    )


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
        # Phase 51.6 §6: the channel site is `scripted` — reaching into the failing
        # forge-mind and slipping costs authored Weird stress, nothing else.
        reaction_policy="scripted",
        reaction_bindings=[
            ObjectReactionBinding(
                binding_id=f"{RESONANCE_OBJECT_ID}:miss",
                object_id=RESONANCE_OBJECT_ID,
                action_verb="*",
                outcome="miss",
                stress_track="weird",
                stress_amount=1,
            )
        ],
    )


def seed_dungeon_channel(
    repo: MemoryRepository,
    save_dir: Path,
    campaign_id: str = CAMPAIGN_ID,
) -> tuple[str | None, str | None]:
    """Seed the dungeon-voice channel + intimacy ladder into ``campaign_id``.

    Returns the persona refs. Idempotent: persona docs, fresh subsystems, and
    objectives are upserted; an objective's earned ``status`` (e.g. ``completed``)
    and a player-restored subsystem's state are **preserved** across re-runs.
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

    _seed_subsystems(repo, campaign_id)
    _seed_objectives(repo, campaign_id)
    _seed_intimacy_clock(repo, campaign_id)

    repo.save_room_object(_resonance_object())

    return voice_ref, knowledge_ref


def _seed_subsystems(repo: MemoryRepository, campaign_id: str) -> None:
    """Author the fresh subsystem objects (tiers 1-3), preserving play state.

    Tier 0 adopts the existing Sand-Choked Gearworks, so it is never authored
    here. Reseeding is additive: an already-present subsystem is refreshed to the
    current authored definition (so a legacy single-transition subsystem gains its
    contested approaches) but keeps a ``current_state`` the party has already
    changed — re-running must not reset a subsystem they have restored.
    """
    present = {o["slug"]: o for o in repo.get_objects_for_campaign(campaign_id)}
    for rung in LADDER:
        if rung.room_id is None:
            continue
        obj = _subsystem_object(rung)
        prior = present.get(rung.subsystem_slug)
        if prior is not None:
            obj = obj.model_copy(update={"current_state": prior["current_state"]})
        repo.save_room_object(obj)


def _seed_objectives(repo: MemoryRepository, campaign_id: str) -> None:
    """Author the four ladder objectives; preserve any earned ``status``.

    Fresh: tier 0 ``active``, tiers 1-3 ``locked`` (the ladder activates one tier
    at a time). On re-run an objective keeps its current status so completed
    tiers stay completed.
    """
    prior = {o["slug"]: o["status"] for o in repo.get_objectives(campaign_id)}
    for rung in LADDER:
        status = prior.get(
            rung.objective_slug, "active" if rung.tier == 0 else "locked"
        )
        repo.save_objective(_objective(rung, status))


def _seed_intimacy_clock(repo: MemoryRepository, campaign_id: str) -> None:
    """Re-segment the ``dungeon_intimacy`` clock as a latching tier index (D6).

    ``segments`` = number of tiers; ``filled`` = number of completed objectives;
    ``monotonic=True`` (latching — reverts the Phase 51 wide-open hack). Adopts an
    existing ``dungeon_intimacy`` clock so play_view's first-match read is stable.
    """
    completed = sum(
        1 for o in repo.get_objectives(campaign_id) if o["status"] == "completed"
    )
    existing = next(
        (c for c in repo.get_clocks(campaign_id) if c["category"] == INTIMACY_CATEGORY),
        None,
    )
    if existing is not None:
        repo.save_clock(
            clock_id=existing["clock_id"],
            campaign_id=campaign_id,
            label=existing["label"],
            segments=INTIMACY_SEGMENTS,
            filled=completed,
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
            monotonic=True,
        )
    else:
        repo.save_clock(
            clock_id=INTIMACY_CLOCK_ID,
            campaign_id=campaign_id,
            label="The Crucible's Regard",
            segments=INTIMACY_SEGMENTS,
            filled=completed,
            category=INTIMACY_CATEGORY,
            clock_level="dungeon",
            stakes="How well the dungeon knows you — and how much it will say.",
            visible_to_player=True,
            monotonic=True,
        )


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
        objectives = repo.get_objectives(CAMPAIGN_ID)
        print(f"Seeded the dungeon channel into The Crucible at {db}")
        print(f"  voice:     {voice_ref}")
        print(f"  knowledge: {knowledge_ref} ({len(DUNGEON_KNOWLEDGE)} secrets)")
        print(
            f"  intimacy:  {clock['filled']}/{clock['segments']} "
            f"(category=dungeon_intimacy, latching tier index)"
        )
        print(f"  ladder:    {len(objectives)} objectives across {INTIMACY_SEGMENTS} tiers")
        for o in objectives:
            print(f"    tier {o['tier_index']} [{o['status']:>9}] {o['title']}")
        print(
            f"  resonance: {RESONANCE_OBJECT_ID} in {RESONANCE_ROOM_ID} "
            f"(Arcane Power Room, Level 2)"
        )
    finally:
        repo.close()


if __name__ == "__main__":
    main()
