from __future__ import annotations

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.patch import ManifestPatch
from dungeon_daddy.campaign.patch_validator import validate_patch


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
        clocks=[
            ClockManifest(slug="final-rite", label="Final Rite Completion", segments=8),
        ],
        memory_seeds=["The party entered through a collapsed side chapel."],
        room_threats=[
            {"location_slug": "nave", "description": "Shades drift between pews."},
        ],
    )


class TestValidPatchReturnsNoErrors:
    def test_empty_patch_on_valid_manifest_returns_no_errors(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch()

        errors = validate_patch(manifest, patch)

        assert errors == []


class TestInvalidActorPatchSurfacesErrors:
    def test_add_actor_with_invalid_action_key_returns_errors(self) -> None:
        manifest = _base_manifest()
        bad_actor = ActorManifest(
            slug="cursed-knight",
            display_name="Cursed Knight",
            actor_type="monster",
            action_ratings={"backstab": 2},
        )
        patch = ManifestPatch(add_actors=[bad_actor])

        errors = validate_patch(manifest, patch)

        assert len(errors) > 0
        fields = [e.field for e in errors]
        assert any("action_ratings" in f for f in fields)


class TestPlayerSideValidation:
    def test_removing_only_player_actor_returns_player_side_error(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(remove_actor_slugs=["valeria"])

        errors = validate_patch(manifest, patch)

        fields = [e.field for e in errors]
        assert any("player_side" in f for f in fields)


class TestRoomThreatReferenceValidation:
    def test_add_room_threat_with_unknown_actor_reference_returns_errors(self) -> None:
        manifest = _base_manifest()
        bad_threat = {
            "location_slug": "crypt",
            "description": "A ghost haunts this room.",
            "related_actor_slugs": ["ghost-that-does-not-exist"],
        }
        patch = ManifestPatch(add_room_threats=[bad_threat])

        errors = validate_patch(manifest, patch)

        assert len(errors) > 0
        assert any("related_actor_slugs" in e.field for e in errors)


class TestPreExistingErrors:
    def test_patch_on_invalid_manifest_surfaces_preexisting_errors(self) -> None:
        invalid_manifest = CampaignManifest(
            slug="broken",
            title="Broken Campaign",
            dungeon_slug="broken",
            player_side=["valeria"],
            world_actors=[
                ActorManifest(
                    slug="valeria",
                    display_name="Valeria",
                    actor_type="pc",
                    action_ratings={"invalid_key": 1},
                ),
            ],
        )
        patch = ManifestPatch(
            add_memory_seeds=["A new seed."],
        )

        errors = validate_patch(invalid_manifest, patch)

        assert len(errors) > 0
        assert any("action_ratings" in e.field for e in errors)
