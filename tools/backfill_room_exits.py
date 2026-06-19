"""Backfill `room_exits` for campaigns published before Phase 48 (Slice 2).

Pre-Phase-48 campaign DBs have no derived exits, so the Play-mode EXITS panel is
empty. This one-time migration re-runs the exit seeder (deriving exits from the
dungeon's `connections`) against an existing campaign DB. It is idempotent and
additive — it only inserts missing exits and never touches actors, memories,
clocks, the session, or any other state.

Newly published campaigns get exits automatically; this is only for old saves.

Usage (close the app first — DuckDB is single-writer):

    python -m tools.backfill_room_exits                 # all campaigns under the default saves dir
    python -m tools.backfill_room_exits "<campaign dir>"  # one campaign (dir with campaign.duckdb + dungeon.json)
    python -m tools.backfill_room_exits --dry-run        # report counts, write nothing
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.seeder import seed_from_manifest
from dungeon_daddy.data.models import Dungeon
from dungeon_daddy.memory.repository import MemoryRepository

_DEFAULT_SAVES = Path.home() / "AppData" / "Local" / "DungeonDaddy" / "saves"
_MIGRATIONS = Path(__file__).resolve().parent.parent / "dungeon_daddy" / "data" / "migrations"


def _campaign_dirs(root: Path) -> list[Path]:
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and (d / "campaign.duckdb").exists() and (d / "dungeon.json").exists()
    )


def _backfill_one(campaign_dir: Path, *, dry_run: bool, force: bool) -> None:
    db_path = campaign_dir / "campaign.duckdb"
    dungeon_path = campaign_dir / "dungeon.json"
    print(f"\n=== {campaign_dir.name} ===")

    repo = MemoryRepository(db_path)
    try:
        repo.initialize_schema(_MIGRATIONS)  # idempotent; ensures room_exits exists

        row = repo._conn.execute(
            "SELECT campaign_id, slug, title FROM campaigns LIMIT 1"
        ).fetchone()
        if row is None:
            print("  No campaign row found — skipping.")
            return
        campaign_id, slug, title = row

        before = repo._conn.execute(
            "SELECT count(*) FROM room_exits WHERE campaign_id = ?", [campaign_id]
        ).fetchone()[0]

        dungeon = Dungeon.model_validate(json.loads(dungeon_path.read_text(encoding="utf-8")))
        manifest = CampaignManifest(slug=slug, title=title, dungeon_slug=slug)

        result = seed_from_manifest(
            manifest, repo, campaign_id, dry_run=dry_run, force=force, dungeon=dungeon,
        )

        print(f"  campaign_id : {campaign_id}")
        print(f"  exits before: {before}")
        print(f"  created     : {result.created}")
        print(f"  updated     : {result.updated}")
        print(f"  skipped     : {result.skipped}")
        for w in result.warnings:
            print(f"  WARNING: {w}")
        if not dry_run:
            after = repo._conn.execute(
                "SELECT count(*) FROM room_exits WHERE campaign_id = ?", [campaign_id]
            ).fetchone()[0]
            print(f"  exits after : {after}")
    finally:
        repo.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill room_exits for pre-Phase-48 campaigns.")
    parser.add_argument(
        "campaign_dir", nargs="?", default=None,
        help="A campaign save directory (containing campaign.duckdb + dungeon.json). "
             "If omitted, all campaigns under the default saves dir are processed.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing.")
    parser.add_argument("--force", action="store_true", help="Re-write existing exits too.")
    args = parser.parse_args()

    if args.campaign_dir is not None:
        dirs = [Path(args.campaign_dir)]
    else:
        if not _DEFAULT_SAVES.exists():
            parser.error(f"Default saves dir not found: {_DEFAULT_SAVES}")
        dirs = _campaign_dirs(_DEFAULT_SAVES)
        if not dirs:
            parser.error(f"No campaigns with campaign.duckdb + dungeon.json under {_DEFAULT_SAVES}")

    print(f"Backfilling room_exits ({'DRY RUN' if args.dry_run else 'WRITE'}) for {len(dirs)} campaign(s).")
    for d in dirs:
        _backfill_one(d, dry_run=args.dry_run, force=args.force)
    print("\nDone.")


if __name__ == "__main__":
    main()
