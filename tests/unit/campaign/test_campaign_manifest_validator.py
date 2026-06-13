from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.validator import ManifestError, validate_manifest


def _valid_manifest(**overrides) -> CampaignManifest:
    """Minimal valid manifest — player_side references an actor that exists."""
    base = dict(
        slug="test-campaign",
        title="Test Campaign",
        dungeon_slug="test-dungeon",
        player_side=["valeria"],
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria", actor_type="pc"),
        ],
        factions=[],
        clocks=[],
        room_threats=[],
    )
    base.update(overrides)
    return CampaignManifest(**base)


def test_valid_manifest_returns_no_errors():
    manifest = _valid_manifest()
    errors = validate_manifest(manifest)
    assert errors == []


def test_duplicate_actor_slugs_across_world_actors_and_factions():
    manifest = _valid_manifest(
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria", actor_type="pc"),
            ActorManifest(slug="warden", display_name="The Warden", actor_type="dungeon"),
        ],
        factions=[
            ActorManifest(slug="warden", display_name="Warden Faction", actor_type="faction"),
        ],
    )
    errors = validate_manifest(manifest)
    assert any("warden" in e.message for e in errors)


def test_duplicate_clock_slugs():
    manifest = _valid_manifest(
        clocks=[
            ClockManifest(slug="doom", label="Doom Clock", segments=6),
            ClockManifest(slug="doom", label="Doom Clock 2", segments=4),
        ]
    )
    errors = validate_manifest(manifest)
    assert any("doom" in e.message for e in errors)


def test_player_side_references_unknown_actor():
    manifest = _valid_manifest(player_side=["ghost"])  # "ghost" not in world_actors
    errors = validate_manifest(manifest)
    assert any("ghost" in e.message for e in errors)


def test_empty_player_side_is_an_error():
    manifest = _valid_manifest(player_side=[])
    errors = validate_manifest(manifest)
    assert any("player_side" in e.field for e in errors)


def test_invalid_action_rating_key_is_an_error():
    manifest = _valid_manifest(
        world_actors=[
            ActorManifest(
                slug="valeria",
                display_name="Valeria",
                actor_type="pc",
                action_ratings={"fight": 2, "dragon_breath": 1},  # invalid key
            ),
        ],
    )
    errors = validate_manifest(manifest)
    assert any("dragon_breath" in e.message for e in errors)


def test_invalid_stress_track_key_is_an_error():
    manifest = _valid_manifest(
        world_actors=[
            ActorManifest(
                slug="valeria",
                display_name="Valeria",
                actor_type="pc",
                stress_tracks=[
                    {"track_key": "body"},
                    {"track_key": "shadow"},  # invalid
                ],
            ),
        ],
    )
    errors = validate_manifest(manifest)
    assert any("shadow" in e.message for e in errors)


def test_clock_with_zero_segments_is_an_error():
    manifest = _valid_manifest(
        clocks=[ClockManifest(slug="bad-clock", label="Bad Clock", segments=0)]
    )
    errors = validate_manifest(manifest)
    assert any("bad-clock" in e.message for e in errors)


def test_room_threat_references_unknown_actor_slug():
    manifest = _valid_manifest(
        room_threats=[
            {
                "location_slug": "R1",
                "related_actor_slugs": ["valeria", "ghost-goblin"],  # ghost-goblin unknown
                "related_clock_slugs": [],
            }
        ]
    )
    errors = validate_manifest(manifest)
    assert any("ghost-goblin" in e.message for e in errors)


def test_room_threat_references_unknown_clock_slug():
    manifest = _valid_manifest(
        clocks=[ClockManifest(slug="doom", label="Doom", segments=6)],
        room_threats=[
            {
                "location_slug": "R1",
                "related_actor_slugs": [],
                "related_clock_slugs": ["doom", "phantom-clock"],  # phantom-clock unknown
            }
        ],
    )
    errors = validate_manifest(manifest)
    assert any("phantom-clock" in e.message for e in errors)
