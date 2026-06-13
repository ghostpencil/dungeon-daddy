"""Validate a campaign manifest or DB/Markdown sync.

Manifest validation (Phase 40):
    python tools/validate_campaign.py --manifest path/to/campaign_manifest.json

DB/Markdown sync validation (legacy):
    python tools/validate_campaign.py db_path memory_root
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.sync import SyncIssue, SyncReporter

_MIGRATIONS = Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"


def validate_campaign(repo: MemoryRepository, memory_root: Path) -> list[SyncIssue]:
    """Return drift issues (missing_file and orphan_markdown only)."""
    reporter = SyncReporter(repo, memory_root)
    all_issues = reporter.check()
    return [i for i in all_issues if i.kind in {"missing_file", "orphan_markdown"}]


def validate_manifest_file(manifest_path: Path) -> int:
    """Validate a campaign manifest JSON file. Returns exit code (0 = ok)."""
    from dungeon_daddy.campaign.manifest import CampaignManifest
    from dungeon_daddy.campaign.validator import validate_manifest

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = CampaignManifest(**raw)
    except Exception as exc:
        print(f"ERROR: failed to parse manifest: {exc}", file=sys.stderr)
        return 1

    errors = validate_manifest(manifest)
    if not errors:
        print(f"OK: {manifest_path.name} is valid ({manifest.slug!r})")
        return 0

    print(f"INVALID: {manifest_path.name} has {len(errors)} error(s):")
    for err in errors:
        print(f"  {err.field}: {err.message}")
    return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate a campaign manifest or DB/Markdown sync."
    )
    subparsers = parser.add_subparsers(dest="mode")

    # Manifest validation mode
    manifest_p = subparsers.add_parser("--manifest", help="Validate a manifest file")

    # Support both: validate_campaign.py --manifest path AND the legacy positional args
    # We handle --manifest as a top-level flag too, for convenience
    parser.add_argument("--manifest", metavar="PATH", help="Validate a campaign manifest JSON file")
    parser.add_argument("db_path", nargs="?", help="Path to campaign.duckdb (legacy sync mode)")
    parser.add_argument("memory_root", nargs="?", help="Path to rpg-memory/ folder (legacy sync mode)")

    args = parser.parse_args()

    if args.manifest:
        sys.exit(validate_manifest_file(Path(args.manifest)))

    if args.db_path and args.memory_root:
        r = MemoryRepository(Path(args.db_path))
        r.initialize_schema(_MIGRATIONS)
        issues = validate_campaign(r, Path(args.memory_root))
        r.close()
        if not issues:
            print("OK: no drift detected")
            sys.exit(0)
        for issue in issues:
            print(f"  {issue.kind}: memory_id={issue.memory_id} path={issue.path} ({issue.detail})")
        sys.exit(1)

    parser.print_help()
    sys.exit(1)
