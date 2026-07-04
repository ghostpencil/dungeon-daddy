from __future__ import annotations

import json
import shutil
from pathlib import Path

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.seeder import seed_from_manifest
from dungeon_daddy.campaign.validator import validate_manifest
from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.dungeon_persona import (
    write_dungeon_knowledge,
    write_dungeon_voice,
)
from dungeon_daddy.memory.repository import MemoryRepository


class PublishError(Exception):
    pass


def publish_save(
    manifest: CampaignManifest,
    dungeons_dir: Path,
    saves_dir: Path,
    save_slug: str,
    migrations_dir: Path,
) -> str:
    """Publish a campaign seed to a self-contained save game. Returns save_slug."""
    if not manifest.dungeon_slug:
        raise PublishError("manifest.dungeon_slug must not be empty")
    errors = validate_manifest(manifest)
    if errors:
        messages = "; ".join(f"{e.field}: {e.message}" for e in errors)
        raise PublishError(f"Manifest validation failed: {messages}")

    save_dir = saves_dir / save_slug
    save_dir.mkdir(parents=True, exist_ok=True)

    _copy_dungeon_design(dungeons_dir / manifest.dungeon_slug, save_dir)

    _write_campaign_json(manifest, save_dir)

    _seed_duckdb(manifest, save_slug, save_dir, migrations_dir)

    _write_session_json(save_slug, save_dir)

    return save_slug


def _copy_dungeon_design(src_dir: Path, dst_dir: Path) -> None:
    shutil.copy2(src_dir / "dungeon.json", dst_dir / "dungeon.json")
    for filename in ["setting.md", "party.md"]:
        src = src_dir / filename
        if src.exists():
            shutil.copy2(src, dst_dir / filename)
    for src in src_dir.glob("level_*_design.md"):
        shutil.copy2(src, dst_dir / src.name)


def _write_campaign_json(manifest: CampaignManifest, save_dir: Path) -> None:
    data = json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False)
    (save_dir / "campaign.json").write_text(data, encoding="utf-8")


def _seed_duckdb(
    manifest: CampaignManifest,
    campaign_id: str,
    save_dir: Path,
    migrations_dir: Path,
) -> None:
    repo = MemoryRepository(save_dir / "campaign.duckdb")
    repo.initialize_schema(migrations_dir)
    voice_path, knowledge_path = _write_dungeon_persona(manifest, save_dir, campaign_id)
    repo.save_campaign(
        campaign_id=campaign_id,
        slug=manifest.slug,
        title=manifest.title,
        dungeon_slug=manifest.dungeon_slug,
        dungeon_voice_path=voice_path,
        dungeon_knowledge_path=knowledge_path,
    )
    seed_from_manifest(manifest, repo, campaign_id)


def _write_dungeon_persona(
    manifest: CampaignManifest, save_dir: Path, campaign_id: str
) -> tuple[str | None, str | None]:
    """Write the dungeon persona docs (when authored) and return save-relative refs."""
    dungeon_dir = save_dir / "memory" / "dungeon"
    voice_ref: str | None = None
    knowledge_ref: str | None = None
    if manifest.dungeon_voice:
        path = write_dungeon_voice(dungeon_dir, campaign_id, manifest.dungeon_voice)
        voice_ref = path.relative_to(save_dir).as_posix()
    if manifest.dungeon_knowledge:
        path = write_dungeon_knowledge(
            dungeon_dir, campaign_id, manifest.dungeon_knowledge
        )
        knowledge_ref = path.relative_to(save_dir).as_posix()
    return voice_ref, knowledge_ref


def _write_session_json(save_slug: str, save_dir: Path) -> None:
    state = SessionState(dungeon_id=save_slug)
    data = json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=False)
    (save_dir / "session.json").write_text(data, encoding="utf-8")
