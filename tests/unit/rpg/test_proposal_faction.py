"""Tests for AdjustReputationChange — Slice 4: proposal system faction support."""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.rpg.proposal import AdjustReputationChange, LLMReactionProposal

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


class TestAdjustReputationChangeParsing:
    def test_parses_from_json_via_discriminator(self):
        proposal = LLMReactionProposal.model_validate({
            "narration_hint": "The cult marks you as enemies.",
            "proposed_changes": [
                {
                    "kind": "adjust_reputation",
                    "faction_slug": "ossuary-cult",
                    "delta_steps": -1,
                    "reason": "Party killed two cult members in the nave.",
                }
            ],
        })

        assert len(proposal.proposed_changes) == 1
        change = proposal.proposed_changes[0]
        assert isinstance(change, AdjustReputationChange)
        assert change.faction_slug == "ossuary-cult"
        assert change.delta_steps == -1
        assert change.reason == "Party killed two cult members in the nave."


class TestValidateReputationChange:
    def test_unknown_faction_slug_is_rejected(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        proposal = LLMReactionProposal(
            narration_hint="The cult is displeased.",
            proposed_changes=[
                AdjustReputationChange(
                    faction_slug="ghost-faction",
                    delta_steps=-1,
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_faction_slugs={"ossuary-cult"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "ghost-faction" in result.rejected[0].reason

    def test_known_faction_slug_is_accepted(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        proposal = LLMReactionProposal(
            narration_hint="The cult is displeased.",
            proposed_changes=[
                AdjustReputationChange(
                    faction_slug="ossuary-cult",
                    delta_steps=-1,
                    reason="Party killed two cult members.",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_faction_slugs={"ossuary-cult"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].faction_slug == "ossuary-cult"


class TestApplyReputationChange:
    def _repo_with_faction(self, tmp_path, slug: str = "ossuary-cult", reputation: str = "neutral"):
        from dungeon_daddy.memory.repository import MemoryRepository
        from dungeon_daddy.rpg.models import FactionState

        repo = MemoryRepository(tmp_path / "test.duckdb")
        repo.initialize_schema(MIGRATIONS_DIR)
        repo.save_faction(FactionState(
            faction_id="faction_ossuary",
            campaign_id="campaign_1",
            slug=slug,
            display_name="The Ossuary Cult",
            reputation=reputation,
        ))
        return repo

    def test_apply_updates_faction_reputation_in_db(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = self._repo_with_faction(tmp_path, reputation="neutral")
        change = AdjustReputationChange(
            faction_slug="ossuary-cult",
            delta_steps=-1,
            reason="Party killed two cult members.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        factions = repo.get_factions("campaign_1")
        assert factions[0]["reputation"] == "cold"

    def test_apply_emits_reputation_changed_domain_event(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = self._repo_with_faction(tmp_path, reputation="cold")
        change = AdjustReputationChange(
            faction_slug="ossuary-cult",
            delta_steps=1,
            reason="Party helped recover stolen relics.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_result = apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        events = repo.get_domain_events("campaign_1")
        rep_events = [e for e in events if e.event_type == "reputation_changed"]
        assert len(rep_events) == 1
        assert rep_events[0].payload["faction_slug"] == "ossuary-cult"
        assert rep_events[0].payload["delta_steps"] == 1
        assert rep_events[0].payload["reason"] == "Party helped recover stolen relics."
        assert len(apply_result.events) == 1

    def test_apply_clamps_reputation_at_allied(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = self._repo_with_faction(tmp_path, reputation="warm")
        change = AdjustReputationChange(
            faction_slug="ossuary-cult",
            delta_steps=3,
            reason="Great deeds in service of the cult.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="campaign_1")

        factions = repo.get_factions("campaign_1")
        assert factions[0]["reputation"] == "allied"
