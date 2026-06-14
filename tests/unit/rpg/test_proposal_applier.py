"""Tests for ProposalApplier — Slices 5 & 6."""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.proposal import (
    AdvanceClockChange,
    ApplyConsequenceChange,
    CreateMemoryChange,
)
from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
from dungeon_daddy.rpg.proposal_validator import ValidationResult

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


def _repo(tmp_path: Path) -> MemoryRepository:
    repo = MemoryRepository(tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    return repo


class TestCreateMemoryAutoApplied:
    def test_create_memory_saved_with_draft_status(self, tmp_path):
        repo = _repo(tmp_path)
        change = CreateMemoryChange(
            title="Mara found the sigil",
            summary="Hidden under the moss.",
            importance=3,
            tags=["actor:pc:mara"],
        )
        result = ValidationResult(accepted=[change], rejected=[], source="llm_draft")

        apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        entries = repo.get_memory_entries_by_campaign("campaign_1")
        assert entries[0]["status"] == "draft"

    def test_create_memory_entry_saved_to_repo(self, tmp_path):
        repo = _repo(tmp_path)
        change = CreateMemoryChange(
            title="Mara crossed the threshold",
            summary="She stepped through and heard the door seal behind her.",
            importance=4,
            tags=["actor:pc:mara"],
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        entries = repo.get_memory_entries_by_campaign("campaign_1")
        assert len(entries) == 1
        assert entries[0]["title"] == "Mara crossed the threshold"
        assert entries[0]["summary"] == "She stepped through and heard the door seal behind her."
        assert entries[0]["importance"] == 4

    def test_tags_saved_for_applied_memory(self, tmp_path):
        repo = _repo(tmp_path)
        change = CreateMemoryChange(
            title="Bone gate opened",
            summary="The sound traveled through stone.",
            importance=5,
            tags=["actor:pc:mara", "location:ossuary_gate", "thread:bone_warden"],
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        entries = repo.get_memory_entries_by_campaign("campaign_1")
        memory_id = entries[0]["memory_id"]
        tags = repo.get_memory_tags(memory_id)
        assert set(tags) == {"actor:pc:mara", "location:ossuary_gate", "thread:bone_warden"}

    def test_domain_event_memory_created_is_emitted(self, tmp_path):
        repo = _repo(tmp_path)
        change = CreateMemoryChange(
            title="Mara woke the ossuary hinges",
            summary="The sound alerted something behind the walls.",
            importance=5,
            tags=["actor:pc:mara"],
        )
        result = ValidationResult(accepted=[change], rejected=[], source="llm_draft")

        apply_result = apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        memory_events = [e for e in events if e.event_type == "memory_created"]
        assert len(memory_events) == 1
        assert memory_events[0].payload["title"] == "Mara woke the ossuary hinges"
        assert memory_events[0].payload["source"] == "llm_draft"
        assert len(apply_result.events) == 1  # memory_created (proposal.applied not in apply_result.events)


class TestNonCreateMemorySkipped:
    def test_advance_clock_accepted_goes_to_skipped(self, tmp_path):
        repo = _repo(tmp_path)
        clock_change = AdvanceClockChange(
            clock_id="clock_bone_warden_stirs", amount=1, reason="partial success"
        )
        result = ValidationResult(accepted=[clock_change], rejected=[])

        apply_result = apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        assert apply_result.applied == []
        assert len(apply_result.skipped) == 1
        assert apply_result.skipped[0] is clock_change
        assert apply_result.events == []
        assert repo.get_memory_entries_by_campaign("campaign_1") == []


def _repo_with_actor(tmp_path: Path, actor_id: str = "actor_mara") -> MemoryRepository:
    repo = MemoryRepository(tmp_path / "test.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    repo.save_actor(actor_id, "campaign_1", "pc", "mara", "Mara")
    repo.save_actor_stress_track(actor_id, "body", capacity=4, filled=0)
    return repo


class TestApplyConsequenceNoDuplication:
    """Deterministic reaction is authoritative for stress; proposals must never double-apply."""

    def test_matching_track_skipped_not_applied(self, tmp_path):
        # deterministic "fight" → "body"; LLM re-proposes "body" → must be skipped
        repo = _repo_with_actor(tmp_path)
        change = ApplyConsequenceChange(
            actor_id="actor_mara",
            track_key="body",
            amount=1,
            reason="hit by trap",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_result = apply_low_risk_proposals(
            result, repo=repo, campaign_id="campaign_1", action_key="fight"
        )

        assert apply_result.applied == []
        assert len(apply_result.skipped) == 1
        assert apply_result.skipped[0] is change
        assert apply_result.events == []
        tracks = repo.get_actor_stress_tracks("actor_mara")
        body = next(t for t in tracks if t["track_key"] == "body")
        assert body["filled"] == 0

    def test_no_stress_event_emitted_for_skipped_consequence(self, tmp_path):
        repo = _repo_with_actor(tmp_path)
        change = ApplyConsequenceChange(
            actor_id="actor_mara",
            track_key="body",
            amount=2,
            reason="heavy blow",
        )
        result = ValidationResult(accepted=[change], rejected=[], source="llm_draft")

        apply_result = apply_low_risk_proposals(
            result, repo=repo, campaign_id="campaign_1", action_key="fight"
        )

        assert apply_result.events == []
        assert repo.get_domain_events("campaign_1") == []


class TestProposalAppliedEvent:
    def test_create_memory_emits_proposal_applied_event(self, tmp_path):
        repo = _repo(tmp_path)
        change = CreateMemoryChange(
            title="Test memory",
            summary="Something happened.",
            importance=3,
            tags=[],
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        applied_events = [e for e in events if e.event_type == "proposal.applied"]
        assert len(applied_events) == 1
        assert applied_events[0].payload["kind"] == "create_memory"

    def test_adjust_reputation_emits_proposal_applied_event(self, tmp_path):
        from dungeon_daddy.rpg.proposal import AdjustReputationChange
        from dungeon_daddy.rpg.models import FactionState
        import uuid as _uuid
        repo = _repo(tmp_path)
        faction = FactionState(
            faction_id=str(_uuid.uuid4()),
            campaign_id="camp_x",
            slug="bone-choir",
            display_name="Bone Choir",
        )
        repo.save_faction(faction)
        change = AdjustReputationChange(faction_slug="bone-choir", delta_steps=1, reason="helped them")
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        applied_events = [e for e in events if e.event_type == "proposal.applied"]
        assert len(applied_events) == 1
        assert applied_events[0].payload["kind"] == "adjust_reputation"


class TestApplyConsequenceDivergingTrack:
    def test_diverging_track_stays_draft_not_applied(self, tmp_path):
        repo = _repo_with_actor(tmp_path)
        change = ApplyConsequenceChange(
            actor_id="actor_mara",
            track_key="composure",  # diverges from deterministic "body" for action_key="fight"
            amount=1,
            reason="wrong track proposed",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_result = apply_low_risk_proposals(
            result, repo=repo, campaign_id="campaign_1", action_key="fight"
        )

        assert apply_result.applied == []
        assert len(apply_result.skipped) == 1
        assert apply_result.skipped[0] is change
        assert apply_result.events == []
        tracks = repo.get_actor_stress_tracks("actor_mara")
        body = next(t for t in tracks if t["track_key"] == "body")
        assert body["filled"] == 0
