"""Create a new campaign folder from a slug and title.

Usage:
    python tools/create_campaign.py --slug bone-cathedral --title "The Bone Cathedral"
    python tools/create_campaign.py --slug bone-cathedral --title "The Bone Cathedral" --dry-run
    python tools/create_campaign.py --slug bone-cathedral --title "..." --campaigns-dir /path/to/campaigns
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _find_campaigns_dir() -> Path:
    from platformdirs import user_data_path
    return user_data_path("DungeonDaddy", appauthor=False) / "campaigns"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new campaign folder.")
    parser.add_argument("--slug", required=True, help="URL-safe slug for the campaign")
    parser.add_argument("--title", required=True, help="Human-readable campaign title")
    parser.add_argument("--dry-run", action="store_true", help="Print intended changes without writing")
    parser.add_argument("--campaigns-dir", metavar="PATH", help="Override campaigns directory")
    args = parser.parse_args()

    campaigns_dir = Path(args.campaigns_dir) if args.campaigns_dir else _find_campaigns_dir()

    from dungeon_daddy.campaign.creator import create_campaign_folder

    label = "[dry-run] " if args.dry_run else ""
    print(f"{label}Creating campaign: {args.slug!r} ({args.title})")
    print(f"{label}Campaigns dir: {campaigns_dir}")

    result = create_campaign_folder(args.slug, args.title, campaigns_dir, dry_run=args.dry_run)

    for path in result.created:
        print(f"  {'[would create]' if args.dry_run else 'created:'} {path}")
    for path in result.skipped:
        print(f"  skipped (exists): {path}")

    print(f"\nDone. Created: {len(result.created)}, Skipped: {len(result.skipped)}")


if __name__ == "__main__":
    main()
