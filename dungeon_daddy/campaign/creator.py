"""Campaign folder creator — scaffolds a new campaign directory."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_MIGRATIONS_DIR = (
    Path(__file__).parent.parent / "data" / "migrations"
)


@dataclass
class CreateResult:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    dry_run: bool = False


def create_campaign_folder(
    slug: str,
    title: str,
    campaigns_dir: Path,
    dry_run: bool = False,
) -> CreateResult:
    """Create or patch a campaign folder for slug/title.

    Idempotent — existing files and directories are skipped.
    dry_run=True returns what would be created without writing.
    """
    result = CreateResult(dry_run=dry_run)
    folder = campaigns_dir / slug

    _ensure_dir(folder, result, dry_run)
    _ensure_dir(folder / "memory", result, dry_run)
    _ensure_dir(folder / "rpg-memory", result, dry_run)
    _ensure_db(folder / "campaign.duckdb", result, dry_run)
    _ensure_file(folder / "setting.md", f"# {title}\n\n## Setting\n\n", result, dry_run)
    _ensure_file(folder / "party.md", f"# {title}\n\n## Party\n\n", result, dry_run)

    return result


def _ensure_dir(path: Path, result: CreateResult, dry_run: bool) -> None:
    if path.exists():
        result.skipped.append(str(path))
        return
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)
    result.created.append(str(path))


def _ensure_db(path: Path, result: CreateResult, dry_run: bool) -> None:
    if path.exists():
        result.skipped.append(str(path))
        return
    if not dry_run:
        from dungeon_daddy.memory.repository import MemoryRepository
        repo = MemoryRepository(path)
        repo.initialize_schema(_MIGRATIONS_DIR)
        repo.close()
    result.created.append(str(path))


def _ensure_file(path: Path, content: str, result: CreateResult, dry_run: bool) -> None:
    if path.exists():
        result.skipped.append(str(path))
        return
    if not dry_run:
        path.write_text(content, encoding="utf-8")
    result.created.append(str(path))
