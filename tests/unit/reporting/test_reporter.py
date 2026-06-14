import uuid
from pathlib import Path

import pytest

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.reporting.reporter import build_report


def _evt(campaign_id: str, event_type: str, payload: dict) -> DomainEvent:
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type=event_type,
        payload=payload,
    )


def test_build_report_empty_campaign_returns_valid_report(repo):
    report = build_report(repo, "camp-empty")
    assert report.campaign_id == "camp-empty"
    assert report.action_usage == []
    assert report.stress_distribution == []
    assert report.clock_activity == []
    assert report.fallout_frequency == []
    assert report.outcome_breakdown.critical == 0
    assert report.proposal_stats.applied == 0
    assert report.memory_stats.created == 0


def test_build_report_populates_action_usage(repo):
    campaign_id = "camp-1"
    repo.insert_domain_event(_evt(campaign_id, "action.resolved", {"action_key": "fight", "outcome": "full"}))
    repo.insert_domain_event(_evt(campaign_id, "action.resolved", {"action_key": "fight", "outcome": "miss"}))

    report = build_report(repo, campaign_id)
    assert len(report.action_usage) == 1
    assert report.action_usage[0].action_key == "fight"
    assert report.action_usage[0].count == 2


def test_build_report_campaign_isolation(repo):
    repo.insert_domain_event(_evt("camp-a", "action.resolved", {"action_key": "study", "outcome": "full"}))

    report = build_report(repo, "camp-b")
    assert report.action_usage == []


def test_build_report_generated_at_is_datetime(repo):
    from datetime import datetime
    report = build_report(repo, "camp-x")
    assert isinstance(report.generated_at, datetime)
