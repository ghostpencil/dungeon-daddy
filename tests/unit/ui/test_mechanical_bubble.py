"""Phase 38.6 — Mechanical result chat bubble formatting."""
from __future__ import annotations

from dungeon_daddy.rpg.models import (
    ActionResolution,
    ReactionClockLine,
    ReactionStressLine,
    WorldReaction,
)
from dungeon_daddy.ui.mechanical_bubble import format_mechanical_bubble


def _resolution(
    outcome: str = "partial",
    dice: list[int] | None = None,
    action_key: str = "study",
) -> ActionResolution:
    return ActionResolution(
        resolution_id="r1",
        campaign_id="c1",
        actor_id="a1",
        action_key=action_key,
        dice_rolled=dice if dice is not None else [2, 4, 1],
        outcome=outcome,
    )


# ---------------------------------------------------------------------------
# Slice 1 — Tracer bullet: header format (actor name + action key)
# ---------------------------------------------------------------------------

class TestBubbleHeader:
    def test_header_contains_actor_name(self):
        """Bubble first line names the actor."""
        text = format_mechanical_bubble("Mara", "study", _resolution())
        assert "Mara" in text.splitlines()[0]

    def test_header_contains_action_key_uppercased(self):
        """Bubble first line shows action key in uppercase."""
        text = format_mechanical_bubble("Mara", "study", _resolution())
        assert "STUDY" in text.splitlines()[0]


# ---------------------------------------------------------------------------
# Slice 2 — Human-readable outcome tier name
# ---------------------------------------------------------------------------

class TestOutcomeTierLabel:
    def test_partial_becomes_partial_success(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(outcome="partial"))
        assert "Partial Success" in text
        assert text.count("partial") == 0  # no raw value leaks

    def test_full_becomes_full_success(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(outcome="full"))
        assert "Full Success" in text

    def test_critical_becomes_critical_success(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(outcome="critical"))
        assert "Critical Success" in text

    def test_miss_becomes_miss(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(outcome="miss"))
        assert "Miss" in text


# ---------------------------------------------------------------------------
# Slice 3 — Best die shown in brackets
# ---------------------------------------------------------------------------

class TestBestDieInBrackets:
    def test_best_die_shown(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(dice=[2, 4, 1]))
        assert "[4]" in text

    def test_single_die_shown(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(dice=[6]))
        assert "[6]" in text


# ---------------------------------------------------------------------------
# Slice 4 — No world reaction section when reaction is None
# ---------------------------------------------------------------------------

class TestNoWorldReactionSection:
    def test_no_section_when_reaction_is_none(self):
        text = format_mechanical_bubble("Mara", "study", _resolution(), reaction=None)
        assert "World Reaction" not in text

    def test_no_section_when_reaction_has_no_lines(self):
        reaction = WorldReaction(
            reaction_id="wr1", campaign_id="c1",
            source_resolution_id="r1", outcome="partial",
        )
        text = format_mechanical_bubble("Mara", "study", _resolution(), reaction=reaction)
        assert "World Reaction" not in text


# ---------------------------------------------------------------------------
# Slice 5 — World reaction clock lines
# ---------------------------------------------------------------------------

class TestWorldReactionClockLines:
    def test_clock_line_appears_in_bubble(self):
        reaction = WorldReaction(
            reaction_id="wr1", campaign_id="c1",
            source_resolution_id="r1", outcome="partial",
            clock_lines=[
                ReactionClockLine(
                    clock_id="cl1", label="Bone Warden Stirs",
                    ticks=1, new_filled=3, new_status="active", reason="",
                )
            ],
        )
        text = format_mechanical_bubble("Mara", "study", _resolution(), reaction=reaction)
        assert "World Reaction:" in text
        assert "Bone Warden Stirs +1" in text

    def test_zero_tick_clock_line_omitted(self):
        reaction = WorldReaction(
            reaction_id="wr1", campaign_id="c1",
            source_resolution_id="r1", outcome="partial",
            clock_lines=[
                ReactionClockLine(
                    clock_id="cl1", label="Silent Clock",
                    ticks=0, new_filled=2, new_status="active", reason="",
                )
            ],
        )
        text = format_mechanical_bubble("Mara", "study", _resolution(), reaction=reaction)
        assert "World Reaction" not in text


# ---------------------------------------------------------------------------
# Slice 6 — World reaction stress lines
# ---------------------------------------------------------------------------

class TestWorldReactionStressLines:
    def test_stress_line_appears_in_bubble(self):
        reaction = WorldReaction(
            reaction_id="wr1", campaign_id="c1",
            source_resolution_id="r1", outcome="partial",
            stress_lines=[
                ReactionStressLine(
                    actor_id="a1", display_name="Mara",
                    track_key="body", amount=1, new_filled=2, reason="",
                )
            ],
        )
        text = format_mechanical_bubble("Mara", "study", _resolution(), reaction=reaction)
        assert "World Reaction:" in text
        assert "Mara body +1" in text

    def test_zero_amount_stress_line_omitted(self):
        reaction = WorldReaction(
            reaction_id="wr1", campaign_id="c1",
            source_resolution_id="r1", outcome="partial",
            stress_lines=[
                ReactionStressLine(
                    actor_id="a1", display_name="Mara",
                    track_key="body", amount=0, new_filled=0, reason="",
                )
            ],
        )
        text = format_mechanical_bubble("Mara", "study", _resolution(), reaction=reaction)
        assert "World Reaction" not in text
