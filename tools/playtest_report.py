"""CLI: print a playtest balance report for a given campaign."""
from __future__ import annotations

import sys
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.reporting.models import PlaytestReport
from dungeon_daddy.reporting.reporter import build_report

MIGRATIONS_DIR = Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"


def format_report(report: PlaytestReport) -> str:
    lines: list[str] = []
    lines.append(f"=== Playtest Balance Report: {report.campaign_id} ===")
    lines.append(f"Generated: {report.generated_at.isoformat()}")
    lines.append("")

    lines.append("--- Action Usage ---")
    for row in report.action_usage:
        lines.append(f"{row.action_key:<12} {row.count}")
    if not report.action_usage:
        lines.append("(no data)")
    lines.append("")

    ob = report.outcome_breakdown
    lines.append("--- Outcome Breakdown ---")
    lines.append(f"critical {ob.critical}  full {ob.full}  partial {ob.partial}  miss {ob.miss}")
    lines.append("")

    lines.append("--- Stress Distribution ---")
    for row in report.stress_distribution:
        lines.append(f"{row.actor_id} / {row.track_key:<12} {row.total_marks} marks")
    if not report.stress_distribution:
        lines.append("(no data)")
    lines.append("")

    lines.append("--- Clock Activity ---")
    for row in report.clock_activity:
        lines.append(f'"{row.label}"  {row.times_advanced} advances  [{row.final_status}]')
    if not report.clock_activity:
        lines.append("(no data)")
    lines.append("")

    lines.append("--- Fallout Frequency ---")
    for row in report.fallout_frequency:
        lines.append(f"{row.actor_id} / {row.track_key}  {row.severity}")
    if not report.fallout_frequency:
        lines.append("(no data)")
    lines.append("")

    ps = report.proposal_stats
    lines.append("--- Proposal Stats ---")
    lines.append(f"Applied: {ps.applied}   Rejected: {ps.rejected}")
    for kind, count in ps.by_kind.items():
        lines.append(f"  {kind}: applied={count}")
    lines.append("")

    ms = report.memory_stats
    lines.append("--- Memory Stats ---")
    lines.append(f"Created (events): {ms.created}")
    lines.append(f"draft={ms.draft}  approved={ms.approved}  rejected={ms.rejected}  archived={ms.archived}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("Usage: python tools/playtest_report.py <db_path> <campaign_id>", file=sys.stderr)
        sys.exit(1)
    db_path, campaign_id = Path(args[0]), args[1]
    repo = MemoryRepository(db_path=db_path)
    repo.initialize_schema(MIGRATIONS_DIR)
    try:
        report = build_report(repo, campaign_id)
        print(format_report(report))
    finally:
        repo.close()


if __name__ == "__main__":
    main()
