from __future__ import annotations

from pydantic import BaseModel, Field

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest


class ManifestPatch(BaseModel):
    rationale: str | None = None
    add_actors: list[ActorManifest] = Field(default_factory=list)
    remove_actor_slugs: list[str] = Field(default_factory=list)
    add_clocks: list[ClockManifest] = Field(default_factory=list)
    remove_clock_slugs: list[str] = Field(default_factory=list)
    add_room_threats: list[dict] = Field(default_factory=list)
    remove_room_threat_locations: list[str] = Field(default_factory=list)
    add_memory_seeds: list[str] = Field(default_factory=list)
    remove_memory_seeds: list[str] = Field(default_factory=list)


def apply_patch(manifest: CampaignManifest, patch: ManifestPatch) -> CampaignManifest:
    remove_slugs = set(patch.remove_actor_slugs)
    new_world_actors = [a for a in manifest.world_actors if a.slug not in remove_slugs]
    new_factions = [a for a in manifest.factions if a.slug not in remove_slugs]

    existing_actor_slugs = {a.slug for a in new_world_actors} | {a.slug for a in new_factions}
    for actor in patch.add_actors:
        if actor.slug not in existing_actor_slugs:
            new_world_actors.append(actor)
            existing_actor_slugs.add(actor.slug)

    remove_clocks = set(patch.remove_clock_slugs)
    new_clocks = [c for c in manifest.clocks if c.slug not in remove_clocks]
    existing_clock_slugs = {c.slug for c in new_clocks}
    for clock in patch.add_clocks:
        if clock.slug not in existing_clock_slugs:
            new_clocks.append(clock)
            existing_clock_slugs.add(clock.slug)

    remove_locations = set(patch.remove_room_threat_locations)
    new_threats = [t for t in manifest.room_threats if t.get("location_slug") not in remove_locations]
    existing_locations = {t.get("location_slug") for t in new_threats}
    for threat in patch.add_room_threats:
        loc = threat.get("location_slug")
        if loc not in existing_locations:
            new_threats.append(threat)
            existing_locations.add(loc)

    remove_seeds = set(patch.remove_memory_seeds)
    new_seeds = [s for s in manifest.memory_seeds if s not in remove_seeds]
    existing_seeds = set(new_seeds)
    for seed in patch.add_memory_seeds:
        if seed not in existing_seeds:
            new_seeds.append(seed)
            existing_seeds.add(seed)

    return manifest.model_copy(update={
        "world_actors": new_world_actors,
        "factions": new_factions,
        "clocks": new_clocks,
        "room_threats": new_threats,
        "memory_seeds": new_seeds,
    })
