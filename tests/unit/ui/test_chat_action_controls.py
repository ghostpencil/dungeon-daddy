from __future__ import annotations


def _actor(actions: dict[str, int] | None = None):
    from dungeon_daddy.rpg.models import ActorState
    return ActorState(
        actor_id="a1",
        campaign_id="c1",
        actor_type="pc",
        slug="mara",
        display_name="Mara",
        actions=actions or {},
    )


# ---------------------------------------------------------------------------
# Slice 1 — chip count
# ---------------------------------------------------------------------------

class TestChipCount:
    def test_returns_nine_chips(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(None)
        assert len(chips) == 9

    def test_chips_in_canonical_order(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(None)
        keys = [c.action_key for c in chips]
        assert keys == ["fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"]


# ---------------------------------------------------------------------------
# Slice 3 — labels
# ---------------------------------------------------------------------------

class TestChipLabels:
    def test_labels_are_uppercase_action_keys(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(None)
        for chip in chips:
            assert chip.label == chip.action_key.upper()


# ---------------------------------------------------------------------------
# Slice 4 — ratings with no actor
# ---------------------------------------------------------------------------

class TestChipRatingsNoActor:
    def test_all_ratings_none_when_no_actor(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(None)
        assert all(c.rating is None for c in chips)

    def test_all_ratings_none_when_actor_has_empty_actions(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(_actor(actions={}))
        assert all(c.rating is None for c in chips)


# ---------------------------------------------------------------------------
# Slice 5 — ratings from actor
# ---------------------------------------------------------------------------

class TestChipRatingsFromActor:
    def test_rating_appears_on_matching_chip(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(_actor(actions={"study": 2}))
        study = next(c for c in chips if c.action_key == "study")
        assert study.rating == 2

    def test_unset_action_rating_is_none(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(_actor(actions={"study": 2}))
        fight = next(c for c in chips if c.action_key == "fight")
        assert fight.rating is None

    def test_multiple_ratings_all_reflected(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(_actor(actions={"fight": 1, "tinker": 3, "channel": 2}))
        by_key = {c.action_key: c for c in chips}
        assert by_key["fight"].rating == 1
        assert by_key["tinker"].rating == 3
        assert by_key["channel"].rating == 2

    def test_zero_rating_is_none(self):
        from dungeon_daddy.ui.action_chips import build_action_chips
        chips = build_action_chips(_actor(actions={"sense": 0}))
        sense = next(c for c in chips if c.action_key == "sense")
        assert sense.rating is None
