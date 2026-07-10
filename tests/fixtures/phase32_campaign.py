"""Phase 32 golden fixture — seed_campaign(repo) populates a MemoryRepository
with a canonical campaign state used by all Phase 32 tests."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import FalloutRecord

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)

CAMPAIGN_ID = "camp-32"
SABLE_ID = "actor-sable"
INFORMANT_ID = "actor-informant"
GOLEM_ID = "actor-golem"
DUNGEON_ID = "actor-dungeon"
SCENE_INVESTIGATION_ID = "scene-investigation"
SCENE_SOCIAL_ID = "scene-social"
SCENE_COMBAT_ID = "scene-combat"
CLOCK_RITUAL_ID = "clock-ritual"
FALLOUT_PHYSICAL_ID = "fallout-physical"
FALLOUT_WEIRD_ID = "fallout-weird"
MEM_SABLE_PACT_ID = "mem-sable-pact"
MEM_GOLEM_LORE_ID = "mem-golem-lore"
MEM_INFORMANT_ID = "mem-informant"
MEM_OLD_SECRET_ID = "mem-old-secret"
MEM_SIDE_NOTE_ID = "mem-side-note"


@dataclass
class Phase32IDs:
    campaign_id: str
    sable_id: str
    informant_id: str
    golem_id: str
    dungeon_id: str
    scene_investigation_id: str
    scene_social_id: str
    scene_combat_id: str
    clock_ritual_id: str
    fallout_physical_id: str
    fallout_weird_id: str
    mem_sable_pact_id: str
    mem_golem_lore_id: str
    mem_informant_id: str
    mem_old_secret_id: str
    mem_side_note_id: str


def seed_campaign(repo: MemoryRepository) -> Phase32IDs:
    """Seed *repo* with the Phase 32 golden fixture. Returns all IDs."""
    repo.save_campaign(
        CAMPAIGN_ID, "iron-vault-32", "Iron Vault — Phase 32",
        dungeon_slug="iron-vault",
    )

    # PC: Sable — action ratings spread across all tracks
    repo.save_actor(SABLE_ID, CAMPAIGN_ID, "pc", "sable", "Sable")
    for action_key, rating in [
        ("skirmish", 2), ("prowl", 3), ("attune", 1), ("command", 1),
        ("consort", 0), ("sway", 2), ("finesse", 2), ("study", 1),
        ("survey", 1), ("tinker", 0), ("wreck", 1), ("hunt", 2),
    ]:
        repo.save_actor_action_rating(SABLE_ID, action_key, rating)
    for track_key, capacity, filled in [
        ("body", 6, 3), ("composure", 6, 2), ("bonds", 6, 1), ("weird", 6, 4),
    ]:
        repo.save_actor_stress_track(SABLE_ID, track_key, capacity, filled)

    # NPC: Informant — low threat
    repo.save_actor(INFORMANT_ID, CAMPAIGN_ID, "npc", "informant", "The Informant")
    repo.save_actor_stress_track(INFORMANT_ID, "body", 4, 0)

    # Monster: Shard Golem — combat-capable
    repo.save_actor(GOLEM_ID, CAMPAIGN_ID, "monster", "shard-golem", "Shard Golem")
    repo.save_actor_stress_track(GOLEM_ID, "body", 8, 0)

    # Dungeon emotional state: Dread intensity 7
    repo.save_actor(DUNGEON_ID, CAMPAIGN_ID, "dungeon", "iron-vault", "Iron Vault")
    repo.save_actor_stress_track(DUNGEON_ID, "dread", 10, 7)

    # Scenes: investigation, social, combat
    for scene_id, location_slug, status in [
        (SCENE_INVESTIGATION_ID, "library-annex", "completed"),
        (SCENE_SOCIAL_ID, "tavern", "completed"),
        (SCENE_COMBAT_ID, "forge-floor", "active"),
    ]:
        repo._conn.execute(
            "INSERT INTO scenes (scene_id, campaign_id, location_slug, status)"
            " VALUES (?, ?, ?, ?)",
            [scene_id, CAMPAIGN_ID, location_slug, status],
        )

    # Clock: 5-segment ritual, 2 filled
    repo.save_clock(CLOCK_RITUAL_ID, CAMPAIGN_ID, "Awakening Ritual", 5, 2, "active")

    # Fallout: Physical (body) moderate
    repo.save_fallout_record(FalloutRecord(
        fallout_id=FALLOUT_PHYSICAL_ID,
        campaign_id=CAMPAIGN_ID,
        actor_id=SABLE_ID,
        track_key="body",
        severity="moderate",
        title="Cracked Ribs",
        summary="Sable took a heavy blow from the Golem. Movement is painful.",
    ))

    # Fallout: Weird severe
    repo.save_fallout_record(FalloutRecord(
        fallout_id=FALLOUT_WEIRD_ID,
        campaign_id=CAMPAIGN_ID,
        actor_id=SABLE_ID,
        track_key="weird",
        severity="severe",
        title="Fractured Sight",
        summary="Sable's perception bleeds between layers of reality.",
    ))

    # Memory entries at varying importance (including one ≥ 9)
    repo.save_memory_entry(
        MEM_SABLE_PACT_ID, CAMPAIGN_ID, "event", "The Binding Pact",
        summary="Sable swore an oath to the Vault-Keeper in exchange for passage.",
        status="approved", importance=9,
    )
    repo.add_memory_tag(MEM_SABLE_PACT_ID, "actor:pc:sable")

    repo.save_memory_entry(
        MEM_GOLEM_LORE_ID, CAMPAIGN_ID, "lore", "Shard Golem Origin",
        summary="The golems were constructed during the Second Forging to guard the forge-floor.",
        status="approved", importance=7,
    )
    repo.add_memory_tag(MEM_GOLEM_LORE_ID, "location:forge-floor")

    repo.save_memory_entry(
        MEM_INFORMANT_ID, CAMPAIGN_ID, "npc", "The Informant",
        summary="Nervous courier who knows the vault layout but won't say how.",
        status="approved", importance=6,
    )
    repo.add_memory_tag(MEM_INFORMANT_ID, "actor:npc:informant")

    repo.save_memory_entry(
        MEM_OLD_SECRET_ID, CAMPAIGN_ID, "lore", "Hidden Cache",
        summary="Rumour of valuables hidden in the library annex.",
        status="approved", importance=5,
    )
    repo.add_memory_tag(MEM_OLD_SECRET_ID, "location:library-annex")

    repo.save_memory_entry(
        MEM_SIDE_NOTE_ID, CAMPAIGN_ID, "event", "Overheard Argument",
        summary="Two guards arguing near the tavern entrance.",
        status="approved", importance=3,
    )

    return Phase32IDs(
        campaign_id=CAMPAIGN_ID,
        sable_id=SABLE_ID,
        informant_id=INFORMANT_ID,
        golem_id=GOLEM_ID,
        dungeon_id=DUNGEON_ID,
        scene_investigation_id=SCENE_INVESTIGATION_ID,
        scene_social_id=SCENE_SOCIAL_ID,
        scene_combat_id=SCENE_COMBAT_ID,
        clock_ritual_id=CLOCK_RITUAL_ID,
        fallout_physical_id=FALLOUT_PHYSICAL_ID,
        fallout_weird_id=FALLOUT_WEIRD_ID,
        mem_sable_pact_id=MEM_SABLE_PACT_ID,
        mem_golem_lore_id=MEM_GOLEM_LORE_ID,
        mem_informant_id=MEM_INFORMANT_ID,
        mem_old_secret_id=MEM_OLD_SECRET_ID,
        mem_side_note_id=MEM_SIDE_NOTE_ID,
    )
