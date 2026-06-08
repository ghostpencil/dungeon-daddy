"""Tests for LLMReactionProposal and ProposedChange Pydantic models."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from dungeon_daddy.rpg.proposal import (
    AdvanceClockChange,
    CreateMemoryChange,
    LLMReactionProposal,
    parse_proposal,
)


def _base_proposal(**overrides) -> dict:
    return {
        "narration_hint": "Something stirs in the dark.",
        "proposed_changes": [],
        **overrides,
    }


class TestCreateMemoryChange:
    def test_parse_create_memory_change(self):
        proposal = LLMReactionProposal.model_validate(
            _base_proposal(
                proposed_changes=[
                    {
                        "kind": "create_memory",
                        "title": "Mara woke the ossuary hinges",
                        "summary": "Mara opened the ossuary gate, alerting something behind the walls.",
                        "importance": 5,
                        "tags": ["actor:pc:mara", "location:ossuary_gate"],
                    }
                ]
            )
        )
        change = proposal.proposed_changes[0]
        assert isinstance(change, CreateMemoryChange)
        assert change.title == "Mara woke the ossuary hinges"
        assert change.importance == 5
        assert "actor:pc:mara" in change.tags


class TestMultiChangeProposal:
    def test_parse_proposal_with_multiple_change_kinds(self):
        proposal = LLMReactionProposal.model_validate(
            _base_proposal(
                proposed_changes=[
                    {
                        "kind": "advance_clock",
                        "clock_id": "clock_ritual",
                        "amount": 2,
                        "reason": "Ritual progresses",
                    },
                    {
                        "kind": "create_memory",
                        "title": "Ritual advanced",
                        "summary": "The ritual moved closer to completion.",
                        "importance": 4,
                        "tags": ["thread:ritual"],
                    },
                    {
                        "kind": "npc_reaction",
                        "npc_id": "npc_warden",
                        "reaction": "The warden turns its hollow sockets toward the sound.",
                        "reason": "Noise triggered awareness",
                    },
                ]
            )
        )
        assert len(proposal.proposed_changes) == 3
        kinds = [c.kind for c in proposal.proposed_changes]
        assert kinds == ["advance_clock", "create_memory", "npc_reaction"]
        assert proposal.source == "llm_draft"


class TestInvalidProposals:
    def test_unknown_kind_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LLMReactionProposal.model_validate(
                _base_proposal(
                    proposed_changes=[
                        {"kind": "explode_dungeon", "target": "everything"}
                    ]
                )
            )

    def test_missing_required_field_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LLMReactionProposal.model_validate(
                _base_proposal(
                    proposed_changes=[
                        {
                            "kind": "advance_clock",
                            # clock_id is missing
                            "amount": 1,
                            "reason": "something",
                        }
                    ]
                )
            )


class TestAdvanceClockChange:
    def test_parse_advance_clock_change(self):
        proposal = LLMReactionProposal.model_validate(
            _base_proposal(
                proposed_changes=[
                    {
                        "kind": "advance_clock",
                        "clock_id": "clock_bone_warden_stirs",
                        "amount": 1,
                        "reason": "Partial success consequence",
                    }
                ]
            )
        )
        change = proposal.proposed_changes[0]
        assert isinstance(change, AdvanceClockChange)
        assert change.clock_id == "clock_bone_warden_stirs"
        assert change.amount == 1
        assert change.reason == "Partial success consequence"


class TestParseProposal:
    def test_valid_json_returns_proposal(self):
        raw = json.dumps(
            {
                "narration_hint": "Something stirs.",
                "proposed_changes": [],
            }
        )
        result = parse_proposal(raw)
        assert isinstance(result, LLMReactionProposal)
        assert result.narration_hint == "Something stirs."

    def test_malformed_json_returns_none(self):
        assert parse_proposal("{not valid json!!!") is None

    def test_wrong_schema_returns_none(self):
        # valid JSON, but missing required `proposed_changes`
        raw = json.dumps({"narration_hint": "Something stirs."})
        assert parse_proposal(raw) is None

    def test_empty_string_returns_none(self):
        assert parse_proposal("") is None
