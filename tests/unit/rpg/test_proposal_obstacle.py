"""Tests for the constrained ResolveObstacleChange proposal (Phase 51.5 Part B).

The DM (LLM) may propose resolving an obstacle, but only to its **authored**
resolved state — it cannot invent object states. This is the single narrowly-
constrained exception to the "LLM never mutates object state" boundary.
"""
from __future__ import annotations

from dungeon_daddy.rpg.proposal import (
    LLMReactionProposal,
    ResolveObstacleChange,
    parse_proposal,
)
from dungeon_daddy.rpg.proposal_validator import validate_proposal


def _resolve_proposal(object_slug: str, to_state: str) -> LLMReactionProposal:
    return LLMReactionProposal(
        narration_hint="The obstacle gives way.",
        proposed_changes=[
            ResolveObstacleChange(
                object_slug=object_slug,
                to_state=to_state,
                reason="A plausibly-described action overcomes it.",
            )
        ],
    )


class TestResolveObstacleModel:
    def test_parses_and_discriminates_by_kind(self):
        raw = (
            '{"narration_hint": "The gearworks grind free.", '
            '"proposed_changes": [{"kind": "resolve_obstacle", '
            '"object_slug": "gearworks", "to_state": "cleared", '
            '"reason": "She braces the housing and levers the seized cog loose."}]}'
        )
        proposal = parse_proposal(raw)

        assert proposal is not None
        assert len(proposal.proposed_changes) == 1
        change = proposal.proposed_changes[0]
        assert isinstance(change, ResolveObstacleChange)
        assert change.kind == "resolve_obstacle"
        assert change.object_slug == "gearworks"
        assert change.to_state == "cleared"


class TestResolveObstacleValidation:
    def test_authored_resolved_state_is_accepted(self):
        proposal = _resolve_proposal("gearworks", "cleared")
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            obstacle_resolved_states={"gearworks": "cleared"},
        )

        assert len(result.accepted) == 1
        assert len(result.rejected) == 0
        assert result.accepted[0].object_slug == "gearworks"

    def test_unknown_obstacle_is_rejected(self):
        proposal = _resolve_proposal("phantom-gate", "cleared")
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            obstacle_resolved_states={"gearworks": "cleared"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "phantom-gate" in result.rejected[0].reason

    def test_invented_state_is_rejected(self):
        # The LLM cannot push the obstacle to a state it did not author.
        proposal = _resolve_proposal("gearworks", "vaporized")
        result = validate_proposal(
            proposal,
            known_clock_ids=set(),
            obstacle_resolved_states={"gearworks": "cleared"},
        )

        assert len(result.accepted) == 0
        assert len(result.rejected) == 1
        assert "vaporized" in result.rejected[0].reason
        assert "cleared" in result.rejected[0].reason
