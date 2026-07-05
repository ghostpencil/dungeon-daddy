from datetime import UTC, datetime
from pathlib import Path

from dungeon_daddy.reporting.models import (
    ActionUsageRow,
    ClockActivityRow,
    FalloutRow,
    MemoryStats,
    OutcomeBreakdown,
    PlaytestReport,
    ProposalStats,
    StressDistributionRow,
)


def _empty_report() -> PlaytestReport:
    return PlaytestReport(
        campaign_id="camp:test",
        generated_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
        action_usage=[],
        outcome_breakdown=OutcomeBreakdown(),
        stress_distribution=[],
        clock_activity=[],
        fallout_frequency=[],
        proposal_stats=ProposalStats(),
        memory_stats=MemoryStats(),
    )


def _full_report() -> PlaytestReport:
    return PlaytestReport(
        campaign_id="camp:test",
        generated_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
        action_usage=[ActionUsageRow(action_key="fight", count=12)],
        outcome_breakdown=OutcomeBreakdown(critical=2, full=5, partial=4, miss=3),
        stress_distribution=[StressDistributionRow(actor_id="pc-mara", track_key="body", total_marks=5)],
        clock_activity=[ClockActivityRow(label="Bone Warden Stirs", clock_id="clk1", times_advanced=4, final_status="completed")],
        fallout_frequency=[FalloutRow(actor_id="pc-mara", track_key="body", severity="minor")],
        proposal_stats=ProposalStats(applied=8, rejected=3, by_kind={"create_memory": 6}),
        memory_stats=MemoryStats(created=6, draft=3, approved=2, rejected=1),
    )


def test_format_report_contains_campaign_id():
    from playtest_report import format_report
    text = format_report(_empty_report())
    assert "camp:test" in text


def test_format_report_contains_all_section_headings():
    from playtest_report import format_report
    text = format_report(_full_report())
    for heading in [
        "Action Usage",
        "Outcome Breakdown",
        "Stress Distribution",
        "Clock Activity",
        "Fallout Frequency",
        "Proposal Stats",
        "Memory Stats",
    ]:
        assert heading in text, f"Missing heading: {heading}"


def test_format_report_on_empty_data_does_not_raise():
    from playtest_report import format_report
    text = format_report(_empty_report())
    assert isinstance(text, str)
    assert len(text) > 0


def test_main_callable_directly(tmp_path):
    from dungeon_daddy.memory.repository import MemoryRepository
    MIGRATIONS_DIR = (
        Path(__file__).parent.parent.parent.parent
        / "dungeon_daddy"
        / "data"
        / "migrations"
    )
    db_path = tmp_path / "test.duckdb"
    repo = MemoryRepository(db_path=db_path)
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.close()

    from playtest_report import main
    main([str(db_path), "camp-empty"])
