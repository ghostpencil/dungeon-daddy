"""Tests for world-reaction item proposals — Phase 46 Slice 8."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Item
from dungeon_daddy.rpg.proposal import (
    GrantItemChange,
    LLMReactionProposal,
    StripItemChange,
    TransformItemChange,
)

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(db_path=tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    return r


def _sword(campaign_id: str = "camp_x") -> Item:
    return Item(
        item_id="item:camp_x:ghost-blade",
        campaign_id=campaign_id,
        slug="ghost-blade",
        display_name="Ghost Blade",
        item_type="dungeon_item",
        description="A blade that phases through armour.",
        owner_actor_id=None,
    )


# ---------------------------------------------------------------------------
# Model parsing
# ---------------------------------------------------------------------------

class TestGrantItemChangeParsing:
    def test_parses_from_json_via_discriminator(self):
        proposal = LLMReactionProposal.model_validate({
            "narration_hint": "A ghostly merchant offers you a blade.",
            "proposed_changes": [
                {
                    "kind": "grant_item",
                    "item_slug": "ghost-blade",
                    "to_actor_id": "actor:crucible:mara",
                    "reason": "Spectral merchant rewarded courage.",
                }
            ],
        })

        assert len(proposal.proposed_changes) == 1
        change = proposal.proposed_changes[0]
        assert isinstance(change, GrantItemChange)
        assert change.item_slug == "ghost-blade"
        assert change.to_actor_id == "actor:crucible:mara"


class TestStripItemChangeParsing:
    def test_parses_from_json_via_discriminator(self):
        proposal = LLMReactionProposal.model_validate({
            "narration_hint": "The djinn snatches the relic.",
            "proposed_changes": [
                {
                    "kind": "strip_item",
                    "item_id": "item:camp_x:ghost-blade",
                    "reason": "Djinn reclaimed its property.",
                }
            ],
        })

        change = proposal.proposed_changes[0]
        assert isinstance(change, StripItemChange)
        assert change.item_id == "item:camp_x:ghost-blade"


class TestTransformItemChangeParsing:
    def test_parses_from_json_via_discriminator(self):
        proposal = LLMReactionProposal.model_validate({
            "narration_hint": "The orb cracks open and reshapes itself.",
            "proposed_changes": [
                {
                    "kind": "transform_item",
                    "item_id": "item:camp_x:dormant-orb",
                    "new_slug": "awakened-orb",
                    "reason": "Orb absorbed the ritual energy.",
                }
            ],
        })

        change = proposal.proposed_changes[0]
        assert isinstance(change, TransformItemChange)
        assert change.item_id == "item:camp_x:dormant-orb"
        assert change.new_slug == "awakened-orb"


# ---------------------------------------------------------------------------
# Validator — GrantItemChange
# ---------------------------------------------------------------------------

class TestGrantItemChangeValidation:
    def _proposal(self, item_slug: str = "ghost-blade", to_actor_id: str = "actor:crucible:mara") -> LLMReactionProposal:
        return LLMReactionProposal(
            narration_hint="The world grants an item.",
            proposed_changes=[
                GrantItemChange(
                    item_slug=item_slug,
                    to_actor_id=to_actor_id,
                    reason="test",
                )
            ],
        )

    def test_unknown_actor_rejected(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_actor_ids={"actor:crucible:other"},
            known_item_slugs={"ghost-blade"},
            dungeon_item_counts={},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "actor:crucible:mara" in result.rejected[0].reason

    def test_unknown_item_slug_rejected(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_actor_ids={"actor:crucible:mara"},
            known_item_slugs={"other-item"},
            dungeon_item_counts={},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "ghost-blade" in result.rejected[0].reason

    def test_actor_at_cap_rejected(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_actor_ids={"actor:crucible:mara"},
            known_item_slugs={"ghost-blade"},
            dungeon_item_counts={"actor:crucible:mara": 10},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "cap" in result.rejected[0].reason.lower()

    def test_valid_grant_accepted(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_actor_ids={"actor:crucible:mara"},
            known_item_slugs={"ghost-blade"},
            dungeon_item_counts={"actor:crucible:mara": 3},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].item_slug == "ghost-blade"


# ---------------------------------------------------------------------------
# Validator — StripItemChange
# ---------------------------------------------------------------------------

class TestStripItemChangeValidation:
    def _proposal(self, item_id: str = "item:camp_x:ghost-blade") -> LLMReactionProposal:
        return LLMReactionProposal(
            narration_hint="The world strips an item.",
            proposed_changes=[StripItemChange(item_id=item_id, reason="test")],
        )

    def test_unknown_item_id_rejected(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_item_ids={"item:camp_x:other"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "item:camp_x:ghost-blade" in result.rejected[0].reason

    def test_known_item_id_accepted(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_item_ids={"item:camp_x:ghost-blade"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0


# ---------------------------------------------------------------------------
# Validator — TransformItemChange
# ---------------------------------------------------------------------------

class TestTransformItemChangeValidation:
    def _proposal(self, item_id: str = "item:camp_x:dormant-orb") -> LLMReactionProposal:
        return LLMReactionProposal(
            narration_hint="The world transforms an item.",
            proposed_changes=[
                TransformItemChange(item_id=item_id, new_slug="awakened-orb", reason="test")
            ],
        )

    def test_unknown_item_id_rejected(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_item_ids={"item:camp_x:other"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "item:camp_x:dormant-orb" in result.rejected[0].reason

    def test_known_item_id_accepted(self):
        from dungeon_daddy.rpg.proposal_validator import validate_proposal

        result = validate_proposal(
            self._proposal(),
            known_clock_ids=set(),
            known_item_ids={"item:camp_x:dormant-orb"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0


# ---------------------------------------------------------------------------
# Applier — GrantItemChange
# ---------------------------------------------------------------------------

class TestGrantItemChangeApplier:
    def test_grant_assigns_owner_in_db(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(_sword())
        change = GrantItemChange(
            item_slug="ghost-blade",
            to_actor_id="actor:crucible:mara",
            reason="Merchant gifted it.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        items = repo.get_items("camp_x")
        blade = next(i for i in items if i["slug"] == "ghost-blade")
        assert blade["owner_actor_id"] == "actor:crucible:mara"

    def test_grant_emits_item_granted_event(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(_sword())
        change = GrantItemChange(
            item_slug="ghost-blade",
            to_actor_id="actor:crucible:mara",
            reason="Merchant gifted it.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        grant_events = [e for e in events if e.event_type == "item.granted"]
        assert len(grant_events) == 1
        assert grant_events[0].payload["item_slug"] == "ghost-blade"
        assert grant_events[0].payload["to_actor_id"] == "actor:crucible:mara"

    def test_grant_emits_proposal_applied_event(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(_sword())
        change = GrantItemChange(
            item_slug="ghost-blade",
            to_actor_id="actor:crucible:mara",
            reason="test",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        applied = [e for e in events if e.event_type == "proposal.applied"]
        assert len(applied) == 1
        assert applied[0].payload["kind"] == "grant_item"


# ---------------------------------------------------------------------------
# Applier — StripItemChange
# ---------------------------------------------------------------------------

class TestStripItemChangeApplier:
    def test_strip_sets_status_lost(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(_sword())
        change = StripItemChange(item_id="item:camp_x:ghost-blade", reason="Djinn reclaimed it.")
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        items = repo.get_items("camp_x")
        blade = next(i for i in items if i["slug"] == "ghost-blade")
        assert blade["status"] == "lost"

    def test_strip_emits_item_stripped_event(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(_sword())
        change = StripItemChange(item_id="item:camp_x:ghost-blade", reason="Djinn reclaimed it.")
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        strip_events = [e for e in events if e.event_type == "item.stripped"]
        assert len(strip_events) == 1
        assert strip_events[0].payload["item_id"] == "item:camp_x:ghost-blade"


# ---------------------------------------------------------------------------
# Applier — TransformItemChange
# ---------------------------------------------------------------------------

class TestTransformItemChangeApplier:
    def _orb(self, campaign_id: str = "camp_x") -> Item:
        return Item(
            item_id="item:camp_x:dormant-orb",
            campaign_id=campaign_id,
            slug="dormant-orb",
            display_name="Dormant Orb",
            item_type="dungeon_item",
            description="An orb that hums faintly.",
        )

    def test_transform_updates_slug_in_db(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(self._orb())
        change = TransformItemChange(
            item_id="item:camp_x:dormant-orb",
            new_slug="awakened-orb",
            reason="Absorbed ritual energy.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        items = repo.get_items("camp_x")
        assert any(i["slug"] == "awakened-orb" for i in items)

    def test_transform_emits_item_transformed_event(self, tmp_path):
        from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
        from dungeon_daddy.rpg.proposal_validator import ValidationResult

        repo = _repo(tmp_path)
        repo.save_item(self._orb())
        change = TransformItemChange(
            item_id="item:camp_x:dormant-orb",
            new_slug="awakened-orb",
            reason="Absorbed ritual energy.",
        )
        result = ValidationResult(accepted=[change], rejected=[])

        apply_low_risk_proposals(result, repo=repo, campaign_id="camp_x")

        events = repo.get_domain_events("camp_x")
        transform_events = [e for e in events if e.event_type == "item.transformed"]
        assert len(transform_events) == 1
        assert transform_events[0].payload["item_id"] == "item:camp_x:dormant-orb"
        assert transform_events[0].payload["new_slug"] == "awakened-orb"
