from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.publish import PublishError, publish_save
from dungeon_daddy.memory.repository import MemoryRepository

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")


def _actor(slug: str = "hero") -> ActorManifest:
    return ActorManifest(slug=slug, display_name="Hero", actor_type="pc")


def _valid_manifest(dungeon_slug: str = "bone-cathedral") -> CampaignManifest:
    return CampaignManifest(
        slug="bone-cathedral-seed",
        title="Bone Cathedral",
        dungeon_slug=dungeon_slug,
        world_actors=[_actor("hero")],
        player_side=["hero"],
    )


def _seed_dungeon(dungeons_dir: Path, slug: str) -> None:
    dungeon_dir = dungeons_dir / slug
    dungeon_dir.mkdir(parents=True)
    (dungeon_dir / "dungeon.json").write_text('{"slug": "bone-cathedral"}', encoding="utf-8")


def test_empty_dungeon_slug_raises(tmp_path: Path) -> None:
    dungeons_dir = tmp_path / "dungeons"
    saves_dir = tmp_path / "saves"
    dungeons_dir.mkdir()
    saves_dir.mkdir()

    manifest = _valid_manifest(dungeon_slug="")

    with pytest.raises(PublishError):
        publish_save(manifest, dungeons_dir, saves_dir, "my-save", _MIGRATIONS_DIR)

    assert not (saves_dir / "my-save").exists()


def test_publish_creates_required_files(tmp_path: Path) -> None:
    dungeons_dir = tmp_path / "dungeons"
    saves_dir = tmp_path / "saves"
    dungeons_dir.mkdir()
    saves_dir.mkdir()
    _seed_dungeon(dungeons_dir, "bone-cathedral")

    publish_save(_valid_manifest(), dungeons_dir, saves_dir, "run-1", _MIGRATIONS_DIR)

    save_dir = saves_dir / "run-1"
    assert (save_dir / "dungeon.json").exists()
    assert (save_dir / "campaign.json").exists()
    assert (save_dir / "campaign.duckdb").exists()
    assert (save_dir / "session.json").exists()


def test_publish_seeds_duckdb(tmp_path: Path) -> None:
    dungeons_dir = tmp_path / "dungeons"
    saves_dir = tmp_path / "saves"
    dungeons_dir.mkdir()
    saves_dir.mkdir()
    _seed_dungeon(dungeons_dir, "bone-cathedral")

    manifest = CampaignManifest(
        slug="bone-cathedral-seed",
        title="Bone Cathedral",
        dungeon_slug="bone-cathedral",
        world_actors=[_actor("hero")],
        player_side=["hero"],
        clocks=[ClockManifest(slug="doom-clock", label="Doom", segments=6)],
        memory_seeds=["The dungeon awakens."],
    )

    publish_save(manifest, dungeons_dir, saves_dir, "run-1", _MIGRATIONS_DIR)

    repo = MemoryRepository(saves_dir / "run-1" / "campaign.duckdb")
    actors = repo.get_actor("actor:bone-cathedral-seed:hero")
    assert actors is not None
    clocks = repo.get_clocks("run-1")
    assert len(clocks) == 1
    assert clocks[0]["clock_id"] == "clock:bone-cathedral-seed:doom-clock"


def test_snapshot_independent_of_source_dungeon(tmp_path: Path) -> None:
    dungeons_dir = tmp_path / "dungeons"
    saves_dir = tmp_path / "saves"
    dungeons_dir.mkdir()
    saves_dir.mkdir()
    _seed_dungeon(dungeons_dir, "bone-cathedral")

    publish_save(_valid_manifest(), dungeons_dir, saves_dir, "run-1", _MIGRATIONS_DIR)

    # Overwrite the source after publish
    (dungeons_dir / "bone-cathedral" / "dungeon.json").write_text(
        '{"slug": "MUTATED"}', encoding="utf-8"
    )

    saved_content = (saves_dir / "run-1" / "dungeon.json").read_text(encoding="utf-8")
    assert "MUTATED" not in saved_content


def test_two_publish_calls_yield_independent_saves(tmp_path: Path) -> None:
    dungeons_dir = tmp_path / "dungeons"
    saves_dir = tmp_path / "saves"
    dungeons_dir.mkdir()
    saves_dir.mkdir()
    _seed_dungeon(dungeons_dir, "bone-cathedral")

    publish_save(_valid_manifest(), dungeons_dir, saves_dir, "run-1", _MIGRATIONS_DIR)
    publish_save(_valid_manifest(), dungeons_dir, saves_dir, "run-2", _MIGRATIONS_DIR)

    # Both saves exist and are separate directories
    assert (saves_dir / "run-1" / "session.json").exists()
    assert (saves_dir / "run-2" / "session.json").exists()

    # Each session.json has the correct dungeon_id
    import json
    s1 = json.loads((saves_dir / "run-1" / "session.json").read_text())
    s2 = json.loads((saves_dir / "run-2" / "session.json").read_text())
    assert s1["dungeon_id"] == "run-1"
    assert s2["dungeon_id"] == "run-2"


def test_invalid_manifest_raises(tmp_path: Path) -> None:
    dungeons_dir = tmp_path / "dungeons"
    saves_dir = tmp_path / "saves"
    dungeons_dir.mkdir()
    saves_dir.mkdir()
    _seed_dungeon(dungeons_dir, "bone-cathedral")

    # empty player_side fails validate_manifest
    manifest = CampaignManifest(
        slug="bone-cathedral-seed",
        title="Bone Cathedral",
        dungeon_slug="bone-cathedral",
        world_actors=[_actor("hero")],
        player_side=[],
    )

    with pytest.raises(PublishError):
        publish_save(manifest, dungeons_dir, saves_dir, "my-save", _MIGRATIONS_DIR)

    assert not (saves_dir / "my-save").exists()
