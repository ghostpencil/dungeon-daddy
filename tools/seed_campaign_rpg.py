"""Seed RPG data from a CampaignManifest into a campaign folder.

Usage:
    python tools/seed_campaign_rpg.py --campaign bone-cathedral --manifest path/to/manifest.json
    python tools/seed_campaign_rpg.py --campaign bone-cathedral --manifest manifest.json --dry-run
    python tools/seed_campaign_rpg.py --campaign bone-cathedral --manifest manifest.json --force
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_MIGRATIONS_DIR = Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"


def _find_campaigns_dir() -> Path:
    from platformdirs import user_data_path
    return user_data_path("DungeonDaddy", appauthor=False) / "campaigns"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed RPG data from a campaign manifest.")
    parser.add_argument("--campaign", required=True, metavar="SLUG",
                        help="Campaign folder slug")
    parser.add_argument("--manifest", required=True, metavar="PATH",
                        help="Path to campaign_manifest.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print intended changes without writing")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing records")
    parser.add_argument("--campaigns-dir", metavar="PATH",
                        help="Override campaigns directory")
    args = parser.parse_args()

    campaigns_dir = Path(args.campaigns_dir) if args.campaigns_dir else _find_campaigns_dir()
    campaign_dir = campaigns_dir / args.campaign
    manifest_path = Path(args.manifest)

    if not campaign_dir.exists():
        print(f"ERROR: campaign folder not found: {campaign_dir}", file=sys.stderr)
        sys.exit(1)

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    from dungeon_daddy.campaign.manifest import CampaignManifest
    from dungeon_daddy.campaign.seeder import seed_from_manifest
    from dungeon_daddy.campaign.validator import validate_manifest
    from dungeon_daddy.memory.repository import MemoryRepository

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = CampaignManifest(**raw)

    # Validate before seeding
    errors = validate_manifest(manifest)
    if errors:
        print("Manifest validation failed:")
        for err in errors:
            print(f"  {err.field}: {err.message}")
        sys.exit(1)

    campaign_id = f"campaign:{manifest.slug}"
    label = "[dry-run] " if args.dry_run else ""
    print(f"{label}Seeding campaign {manifest.slug!r} from {manifest_path.name}")

    if args.dry_run:
        db_path = campaign_dir / "campaign.duckdb"
        repo = MemoryRepository(db_path)
        repo.initialize_schema(_MIGRATIONS_DIR)
        result = seed_from_manifest(manifest, repo, campaign_id, dry_run=True)
        repo.close()
    else:
        db_path = campaign_dir / "campaign.duckdb"
        repo = MemoryRepository(db_path)
        repo.initialize_schema(_MIGRATIONS_DIR)
        # Ensure campaign row exists
        if repo.get_campaign(campaign_id) is None:
            repo.save_campaign(campaign_id, manifest.slug, manifest.title)
        result = seed_from_manifest(manifest, repo, campaign_id, dry_run=False, force=args.force)
        repo.close()

    result.print_summary()


if __name__ == "__main__":
    main()
