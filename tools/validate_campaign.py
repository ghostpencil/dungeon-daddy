"""Validate DB/Markdown sync for a campaign.

Reports memory entries that have a markdown_path in the DB but no corresponding
file on disk, and Markdown files on disk with no corresponding DB entry.
"""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.sync import SyncIssue, SyncReporter


def validate_campaign(repo: MemoryRepository, memory_root: Path) -> list[SyncIssue]:
    """Return drift issues (missing_file and orphan_markdown only)."""
    reporter = SyncReporter(repo, memory_root)
    all_issues = reporter.check()
    return [i for i in all_issues if i.kind in {"missing_file", "orphan_markdown"}]


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate campaign DB/Markdown sync")
    parser.add_argument("db_path", help="Path to campaign.duckdb")
    parser.add_argument("memory_root", help="Path to rpg-memory/ folder")
    args = parser.parse_args()

    _MIGRATIONS = (
        Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"
    )
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
