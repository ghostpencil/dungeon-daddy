from __future__ import annotations

import pytest

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest, FactionManifest
from dungeon_daddy.campaign.patch import ManifestPatch, apply_patch


def _base_manifest() -> CampaignManifest:
    return CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        player_side=["valeria"],
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc"),
            ActorManifest(slug="bone-warden", display_name="The Bone Warden", actor_type="dungeon"),
        ],
        factions=[
            FactionManifest(slug="ossuary-cult", display_name="The Ossuary Cult"),
        ],
        clocks=[
            ClockManifest(slug="final-rite", label="Final Rite Completion", segments=8),
        ],
        memory_seeds=["The party entered through a collapsed side chapel."],
        room_threats=[
            {"location_slug": "nave", "description": "Shades drift between pews."},
        ],
    )


class TestEmptyPatchIsNoOp:
    def test_empty_patch_returns_equivalent_manifest(self) -> None:
        manifest = _base_manifest()
        result = apply_patch(manifest, ManifestPatch())

        assert result.slug == manifest.slug
        assert [a.slug for a in result.world_actors] == [a.slug for a in manifest.world_actors]
        assert [a.slug for a in result.factions] == [a.slug for a in manifest.factions]
        assert [c.slug for c in result.clocks] == [c.slug for c in manifest.clocks]
        assert result.memory_seeds == manifest.memory_seeds
        assert result.room_threats == manifest.room_threats


class TestAddActor:
    def test_add_actor_appears_in_world_actors(self) -> None:
        manifest = _base_manifest()
        new_actor = ActorManifest(
            slug="undead-jailer",
            display_name="The Undead Jailer",
            actor_type="monster",
        )
        patch = ManifestPatch(add_actors=[new_actor])
        result = apply_patch(manifest, patch)

        slugs = [a.slug for a in result.world_actors]
        assert "undead-jailer" in slugs

    def test_original_actors_preserved_after_add(self) -> None:
        manifest = _base_manifest()
        new_actor = ActorManifest(slug="new-npc", display_name="New NPC", actor_type="npc")
        result = apply_patch(manifest, ManifestPatch(add_actors=[new_actor]))

        assert "valeria" in [a.slug for a in result.world_actors]
        assert "bone-warden" in [a.slug for a in result.world_actors]


class TestRemoveActor:
    def test_remove_actor_from_world_actors(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(remove_actor_slugs=["bone-warden"])
        result = apply_patch(manifest, patch)

        assert "bone-warden" not in [a.slug for a in result.world_actors]

    def test_remove_actor_from_factions(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(remove_actor_slugs=["ossuary-cult"])
        result = apply_patch(manifest, patch)

        assert "ossuary-cult" not in [a.slug for a in result.factions]

    def test_remove_nonexistent_actor_is_noop(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(remove_actor_slugs=["ghost-that-never-was"])
        result = apply_patch(manifest, patch)

        assert [a.slug for a in result.world_actors] == [a.slug for a in manifest.world_actors]


class TestAddClock:
    def test_add_clock_appears_in_clocks(self) -> None:
        manifest = _base_manifest()
        new_clock = ClockManifest(slug="cult-ritual", label="Cult Ritual Progress", segments=6)
        result = apply_patch(manifest, ManifestPatch(add_clocks=[new_clock]))

        assert "cult-ritual" in [c.slug for c in result.clocks]

    def test_original_clocks_preserved_after_add(self) -> None:
        manifest = _base_manifest()
        new_clock = ClockManifest(slug="new-clock", label="New Clock", segments=4)
        result = apply_patch(manifest, ManifestPatch(add_clocks=[new_clock]))

        assert "final-rite" in [c.slug for c in result.clocks]


class TestRemoveClock:
    def test_remove_clock_by_slug(self) -> None:
        manifest = _base_manifest()
        result = apply_patch(manifest, ManifestPatch(remove_clock_slugs=["final-rite"]))

        assert "final-rite" not in [c.slug for c in result.clocks]

    def test_remove_nonexistent_clock_is_noop(self) -> None:
        manifest = _base_manifest()
        result = apply_patch(manifest, ManifestPatch(remove_clock_slugs=["no-such-clock"]))

        assert [c.slug for c in result.clocks] == [c.slug for c in manifest.clocks]


class TestAddRoomThreat:
    def test_add_room_threat_appears_in_room_threats(self) -> None:
        manifest = _base_manifest()
        new_threat = {"location_slug": "reliquary", "description": "The Warden performs the rite."}
        result = apply_patch(manifest, ManifestPatch(add_room_threats=[new_threat]))

        locations = [t["location_slug"] for t in result.room_threats]
        assert "reliquary" in locations

    def test_original_threats_preserved_after_add(self) -> None:
        manifest = _base_manifest()
        new_threat = {"location_slug": "crypt", "description": "Bones rattle."}
        result = apply_patch(manifest, ManifestPatch(add_room_threats=[new_threat]))

        locations = [t["location_slug"] for t in result.room_threats]
        assert "nave" in locations


class TestRemoveRoomThreat:
    def test_remove_room_threat_by_location_slug(self) -> None:
        manifest = _base_manifest()
        result = apply_patch(manifest, ManifestPatch(remove_room_threat_locations=["nave"]))

        locations = [t["location_slug"] for t in result.room_threats]
        assert "nave" not in locations

    def test_remove_nonexistent_threat_is_noop(self) -> None:
        manifest = _base_manifest()
        result = apply_patch(manifest, ManifestPatch(remove_room_threat_locations=["no-such-room"]))

        assert result.room_threats == manifest.room_threats


class TestAddMemorySeed:
    def test_add_memory_seed_appears_in_seeds(self) -> None:
        manifest = _base_manifest()
        new_seed = "A fresh handprint in the bone dust near the reliquary stairs."
        result = apply_patch(manifest, ManifestPatch(add_memory_seeds=[new_seed]))

        assert new_seed in result.memory_seeds

    def test_original_seeds_preserved_after_add(self) -> None:
        manifest = _base_manifest()
        original_seed = manifest.memory_seeds[0]
        result = apply_patch(manifest, ManifestPatch(add_memory_seeds=["new seed"]))

        assert original_seed in result.memory_seeds


class TestRemoveMemorySeed:
    def test_remove_memory_seed_by_value(self) -> None:
        manifest = _base_manifest()
        existing_seed = manifest.memory_seeds[0]
        result = apply_patch(manifest, ManifestPatch(remove_memory_seeds=[existing_seed]))

        assert existing_seed not in result.memory_seeds

    def test_remove_nonexistent_seed_is_noop(self) -> None:
        manifest = _base_manifest()
        result = apply_patch(manifest, ManifestPatch(remove_memory_seeds=["never existed"]))

        assert result.memory_seeds == manifest.memory_seeds


class TestIdempotency:
    def test_applying_add_actor_patch_twice_no_duplicates(self) -> None:
        manifest = _base_manifest()
        new_actor = ActorManifest(slug="undead-jailer", display_name="Undead Jailer", actor_type="monster")
        patch = ManifestPatch(add_actors=[new_actor])

        once = apply_patch(manifest, patch)
        twice = apply_patch(once, patch)

        jailer_count = sum(1 for a in twice.world_actors if a.slug == "undead-jailer")
        assert jailer_count == 1

    def test_applying_add_clock_patch_twice_no_duplicates(self) -> None:
        manifest = _base_manifest()
        new_clock = ClockManifest(slug="cult-ritual", label="Cult Ritual", segments=6)
        patch = ManifestPatch(add_clocks=[new_clock])

        once = apply_patch(manifest, patch)
        twice = apply_patch(once, patch)

        ritual_count = sum(1 for c in twice.clocks if c.slug == "cult-ritual")
        assert ritual_count == 1

    def test_applying_remove_patch_twice_is_safe(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(remove_actor_slugs=["bone-warden"])

        once = apply_patch(manifest, patch)
        twice = apply_patch(once, patch)

        assert "bone-warden" not in [a.slug for a in twice.world_actors]

    def test_applying_add_memory_seed_patch_twice_no_duplicates(self) -> None:
        manifest = _base_manifest()
        new_seed = "A fresh handprint in the bone dust."
        patch = ManifestPatch(add_memory_seeds=[new_seed])

        once = apply_patch(manifest, patch)
        twice = apply_patch(once, patch)

        assert twice.memory_seeds.count(new_seed) == 1

    def test_patch_does_not_mutate_original_manifest(self) -> None:
        manifest = _base_manifest()
        original_actor_count = len(manifest.world_actors)
        new_actor = ActorManifest(slug="extra", display_name="Extra", actor_type="npc")

        apply_patch(manifest, ManifestPatch(add_actors=[new_actor]))

        assert len(manifest.world_actors) == original_actor_count


class TestRationale:
    def test_patch_accepts_optional_rationale(self) -> None:
        patch = ManifestPatch(rationale="Adding an undead jailer as requested by the player.")
        assert patch.rationale == "Adding an undead jailer as requested by the player."

    def test_patch_rationale_defaults_to_none(self) -> None:
        patch = ManifestPatch()
        assert patch.rationale is None
