"""Tests for ProposalValidator — Slices 2 & 3: unknown clock/actor reference rejected."""
from __future__ import annotations

from dungeon_daddy.rpg.proposal import (
    AdvanceClockChange,
    ApplyConsequenceChange,
    CreateMemoryChange,
    LLMReactionProposal,
    NpcReactionChange,
)
from dungeon_daddy.rpg.proposal_validator import validate_proposal


def _proposal_with_clock(clock_id: str) -> LLMReactionProposal:
    return LLMReactionProposal(
        narration_hint="Something stirs.",
        proposed_changes=[
            AdvanceClockChange(clock_id=clock_id, amount=1, reason="test")
        ],
    )


class TestKnownClockAccepted:
    def test_advance_clock_known_id_is_accepted(self):
        proposal = _proposal_with_clock("clock_real_one")
        result = validate_proposal(proposal, known_clock_ids={"clock_real_one"})

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].clock_id == "clock_real_one"


class TestNonClockChangesPassThrough:
    def test_create_memory_accepted_regardless_of_clock_ids(self):
        proposal = LLMReactionProposal(
            narration_hint="A memory forms.",
            proposed_changes=[
                CreateMemoryChange(
                    title="Mara crossed the threshold",
                    summary="She stepped through and heard the door seal behind her.",
                    importance=4,
                    tags=["actor:pc:mara"],
                )
            ],
        )
        result = validate_proposal(proposal, known_clock_ids=set())

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].kind == "create_memory"


class TestUnknownClockRejected:
    def test_advance_clock_unknown_id_is_rejected(self):
        proposal = _proposal_with_clock("clock_does_not_exist")
        result = validate_proposal(proposal, known_clock_ids={"clock_real_one"})

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0].change.clock_id == "clock_does_not_exist"
        assert "clock_does_not_exist" in result.rejected[0].reason


class TestKnownActorAccepted:
    def test_apply_consequence_known_actor_id_is_accepted(self):
        proposal = LLMReactionProposal(
            narration_hint="The blow lands hard.",
            proposed_changes=[
                ApplyConsequenceChange(
                    actor_id="actor_mara",
                    track_key="body",
                    amount=1,
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_actor_ids={"actor_mara"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].actor_id == "actor_mara"

    def test_npc_reaction_known_npc_id_is_accepted(self):
        proposal = LLMReactionProposal(
            narration_hint="The warden turns.",
            proposed_changes=[
                NpcReactionChange(
                    npc_id="npc_bone_warden",
                    reaction="hostile",
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_actor_ids={"npc_bone_warden"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].npc_id == "npc_bone_warden"


class TestUnknownActorRejected:
    def test_apply_consequence_unknown_actor_id_is_rejected(self):
        proposal = LLMReactionProposal(
            narration_hint="The blow lands hard.",
            proposed_changes=[
                ApplyConsequenceChange(
                    actor_id="actor_ghost",
                    track_key="body",
                    amount=1,
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_actor_ids={"actor_mara"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0].change.actor_id == "actor_ghost"
        assert "actor_ghost" in result.rejected[0].reason

    def test_npc_reaction_unknown_npc_id_is_rejected(self):
        proposal = LLMReactionProposal(
            narration_hint="The warden turns.",
            proposed_changes=[
                NpcReactionChange(
                    npc_id="npc_phantom_warden",
                    reaction="hostile",
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_actor_ids={"npc_bone_warden"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0].change.npc_id == "npc_phantom_warden"
        assert "npc_phantom_warden" in result.rejected[0].reason


class TestPlayerActorIntentControlRejected:
    def test_npc_reaction_on_player_actor_is_rejected(self):
        proposal = LLMReactionProposal(
            narration_hint="Mara recoils.",
            proposed_changes=[
                NpcReactionChange(
                    npc_id="actor_mara_pc",
                    reaction="flee",
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_actor_ids={"actor_mara_pc"},
            player_actor_ids={"actor_mara_pc"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "player actor" in result.rejected[0].reason.lower()

    def test_npc_reaction_on_npc_actor_is_accepted(self):
        proposal = LLMReactionProposal(
            narration_hint="The warden turns.",
            proposed_changes=[
                NpcReactionChange(
                    npc_id="npc_bone_warden",
                    reaction="hostile",
                    reason="test",
                )
            ],
        )
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            known_actor_ids={"npc_bone_warden"},
            player_actor_ids={"actor_mara_pc"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0


class TestRejectionEvents:
    def test_rejected_change_emits_rejection_event(self):
        proposal = _proposal_with_clock("clock_unknown")
        result = validate_proposal(proposal, known_clock_ids=set())

        assert len(result.rejection_events) == 1
        evt = result.rejection_events[0]
        assert evt.event_type == "proposal.rejected"
        assert "kind" in evt.payload
        assert "reason" in evt.payload

    def test_all_accepted_yields_empty_rejection_events(self):
        proposal = _proposal_with_clock("clock_real")
        result = validate_proposal(proposal, known_clock_ids={"clock_real"})

        assert result.rejection_events == []

    def test_rejection_event_payload_contains_kind(self):
        proposal = _proposal_with_clock("clock_unknown")
        result = validate_proposal(proposal, known_clock_ids=set())

        assert result.rejection_events[0].payload["kind"] == "advance_clock"
