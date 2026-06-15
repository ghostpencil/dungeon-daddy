import pytest
from pydantic import ValidationError

from dungeon_daddy.rpg.models import (
    ActionRating,
    ActionRequest,
    ActionResolution,
    ActorState,
    ClockState,
    FalloutRecord,
    ReactionClockLine,
    ReactionStressLine,
    StressTrack,
    WorldReaction,
)


class TestReactionStressLine:
    def test_triggered_fallout_can_be_set(self) -> None:
        line = ReactionStressLine(
            actor_id="a1",
            display_name="Kira",
            track_key="body",
            amount=2,
            new_filled=4,
            triggered_fallout=True,
            reason="track filled",
        )
        assert line.triggered_fallout is True


class TestWorldReaction:
    def test_constructs_with_empty_lines(self) -> None:
        wr = WorldReaction(
            reaction_id="r1",
            campaign_id="c1",
            source_resolution_id="res1",
            outcome="miss",
        )
        assert wr.clock_lines == []
        assert wr.stress_lines == []
        assert wr.summary_lines == []

    def test_invalid_outcome_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorldReaction(
                reaction_id="r1",
                campaign_id="c1",
                source_resolution_id="res1",
                outcome="great",
            )

    def test_holds_clock_and_stress_lines(self) -> None:
        clock_line = ReactionClockLine(
            clock_id="ck1", label="Heat", ticks=2,
            new_filled=3, new_status="active", reason="miss",
        )
        stress_line = ReactionStressLine(
            actor_id="a1", display_name="Kira", track_key="body",
            amount=2, new_filled=2, reason="miss",
        )
        wr = WorldReaction(
            reaction_id="r1",
            campaign_id="c1",
            source_resolution_id="res1",
            outcome="miss",
            clock_lines=[clock_line],
            stress_lines=[stress_line],
            summary_lines=["Heat Rising: 1→3", "Kira takes 2 body stress"],
        )
        assert len(wr.clock_lines) == 1
        assert len(wr.stress_lines) == 1
        assert len(wr.summary_lines) == 2


class TestActorState:
    def test_constructs_with_required_fields(self) -> None:
        actor = ActorState(
            actor_id="pc_mara",
            campaign_id="camp_001",
            actor_type="pc",
            slug="mara",
            display_name="Mara",
        )
        assert actor.actor_id == "pc_mara"
        assert actor.status == "active"

    def test_all_actor_types_accepted(self) -> None:
        for t in ("pc", "npc", "monster", "dungeon"):
            a = ActorState(
                actor_id="x", campaign_id="c", actor_type=t, slug="s", display_name="D"
            )
            assert a.actor_type == t

    def test_invalid_actor_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ActorState(
                actor_id="x", campaign_id="c", actor_type="dragon", slug="s", display_name="D"
            )

    def test_all_statuses_accepted(self) -> None:
        for s in ("active", "inactive", "dead", "absorbed", "lost"):
            a = ActorState(
                actor_id="x",
                campaign_id="c",
                actor_type="pc",
                slug="s",
                display_name="D",
                status=s,
            )
            assert a.status == s


class TestStressTrack:
    def test_constructs_with_track_key(self) -> None:
        t = StressTrack(track_key="body")
        assert t.track_key == "body"
        assert t.filled == 0

    def test_capacity_defaults_to_four(self) -> None:
        t = StressTrack(track_key="weird")
        assert t.capacity == 4

    def test_filled_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError):
            StressTrack(track_key="body", filled=-1)

    def test_filled_cannot_exceed_capacity(self) -> None:
        with pytest.raises(ValidationError):
            StressTrack(track_key="body", capacity=4, filled=5)

    def test_filled_equal_to_capacity_is_valid(self) -> None:
        t = StressTrack(track_key="body", capacity=6, filled=6)
        assert t.filled == 6


class TestClockState:
    def test_constructs_with_required_fields(self) -> None:
        c = ClockState(clock_id="clk_1", campaign_id="camp_1", label="Ritual", segments=6)
        assert c.filled == 0
        assert c.status == "active"

    def test_filled_cannot_exceed_segments(self) -> None:
        with pytest.raises(ValidationError):
            ClockState(clock_id="c", campaign_id="x", label="L", segments=4, filled=5)

    def test_filled_equal_to_segments_is_valid(self) -> None:
        c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4, filled=4)
        assert c.filled == 4

    def test_status_values(self) -> None:
        for s in ("active", "completed", "abandoned"):
            c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4, status=s)
            assert c.status == s

    def test_clock_level_defaults_to_dungeon(self) -> None:
        c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4)
        assert c.clock_level == "dungeon"

    def test_clock_level_accepts_all_valid_values(self) -> None:
        for level in ("room", "level", "dungeon", "quest", "character", "faction"):
            c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4, clock_level=level)
            assert c.clock_level == level

    def test_clock_level_rejects_invalid_value(self) -> None:
        with pytest.raises(ValidationError):
            ClockState(clock_id="c", campaign_id="x", label="L", segments=4, clock_level="bad")

    def test_stakes_and_completion_effect_stored(self) -> None:
        c = ClockState(
            clock_id="c", campaign_id="x", label="L", segments=4,
            stakes="The room floods.", completion_effect="All future rolls here are harder.",
        )
        assert c.stakes == "The room floods."
        assert c.completion_effect == "All future rolls here are harder."

    def test_optional_level_metadata_defaults(self) -> None:
        c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4)
        assert c.category is None
        assert c.level_id is None
        assert c.owner_actor_id is None
        assert c.stakes is None
        assert c.completion_effect is None
        assert c.visible_to_player is True


class TestActionRating:
    def test_constructs(self) -> None:
        r = ActionRating(actor_id="pc_mara", action_key="fight", rating=2)
        assert r.rating == 2

    def test_rating_defaults_to_zero(self) -> None:
        r = ActionRating(actor_id="x", action_key="fight")
        assert r.rating == 0

    def test_rating_above_three_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ActionRating(actor_id="x", action_key="fight", rating=4)

    def test_rating_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ActionRating(actor_id="x", action_key="fight", rating=-1)


class TestActionRequest:
    def test_intent_defaults_to_none(self) -> None:
        r = ActionRequest(
            campaign_id="c", scene_id=None, actor_id="a",
            action_key="fight",
        )
        assert r.intent is None

    def test_intent_can_be_set(self) -> None:
        r = ActionRequest(
            campaign_id="c", actor_id="a", action_key="sway",
            intent="convince the guard to stand down",
        )
        assert r.intent == "convince the guard to stand down"


class TestActionResolution:
    def test_constructs_with_outcome(self) -> None:
        r = ActionResolution(
            resolution_id="res_1",
            campaign_id="camp_1",
            actor_id="pc_mara",
            action_key="fight",
            dice_rolled=[4, 6],
            outcome="full",
        )
        assert r.outcome == "full"

    def test_all_outcomes_accepted(self) -> None:
        for o in ("critical", "full", "partial", "miss"):
            r = ActionResolution(
                resolution_id="r",
                campaign_id="c",
                actor_id="a",
                action_key="fight",
                dice_rolled=[3],
                outcome=o,
            )
            assert r.outcome == o

    def test_invalid_outcome_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ActionResolution(
                resolution_id="r",
                campaign_id="c",
                actor_id="a",
                action_key="fight",
                dice_rolled=[3],
                outcome="perfect",
            )

    def test_stress_cost_defaults_to_zero(self) -> None:
        r = ActionResolution(
            resolution_id="r",
            campaign_id="c",
            actor_id="a",
            action_key="fight",
            dice_rolled=[3],
            outcome="partial",
        )
        assert r.stress_cost == 0

    def test_intent_defaults_to_none(self) -> None:
        r = ActionResolution(
            resolution_id="r", campaign_id="c", actor_id="a",
            action_key="fight", dice_rolled=[3], outcome="miss",
        )
        assert r.intent is None

    def test_intent_survives_construction(self) -> None:
        r = ActionResolution(
            resolution_id="r", campaign_id="c", actor_id="a",
            action_key="sway", dice_rolled=[4], outcome="partial",
            intent="forge a bond with the warden",
        )
        assert r.intent == "forge a bond with the warden"


class TestFalloutRecord:
    def test_constructs(self) -> None:
        f = FalloutRecord(
            fallout_id="fo_1",
            campaign_id="camp_1",
            actor_id="pc_mara",
            track_key="weird",
            severity="moderate",
            title="Dreams in the cathedral",
            summary="Mara is haunted.",
        )
        assert f.status == "active"

    def test_track_keys(self) -> None:
        for k in ("body", "composure", "bonds", "weird"):
            f = FalloutRecord(
                fallout_id="x",
                campaign_id="c",
                actor_id="a",
                track_key=k,
                severity="minor",
                title="T",
                summary="S",
            )
            assert f.track_key == k

    def test_invalid_track_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FalloutRecord(
                fallout_id="x",
                campaign_id="c",
                actor_id="a",
                track_key="health",
                severity="minor",
                title="T",
                summary="S",
            )

    def test_severity_values(self) -> None:
        for s in ("minor", "moderate", "severe"):
            f = FalloutRecord(
                fallout_id="x",
                campaign_id="c",
                actor_id="a",
                track_key="body",
                severity=s,
                title="T",
                summary="S",
            )
            assert f.severity == s
