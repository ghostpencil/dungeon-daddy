from __future__ import annotations


def _actor(display_name: str = "Mara", stress: dict | None = None, **kw):
    from dungeon_daddy.rpg.models import ActorState
    return ActorState(
        actor_id=kw.get("actor_id", "a1"),
        campaign_id="c1",
        actor_type="pc",
        slug=kw.get("slug", "mara"),
        display_name=display_name,
        stress=stress or {},
    )


def _track(track_key: str, filled: int = 0, capacity: int = 4):
    from dungeon_daddy.rpg.models import StressTrack
    return StressTrack(track_key=track_key, filled=filled, capacity=capacity)


# ---------------------------------------------------------------------------
# Slice 1 — actor name
# ---------------------------------------------------------------------------

class TestActorName:
    def test_returns_display_name(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        card = build_actor_mini_card(_actor("Mara"))
        assert card.actor_name == "Mara"


# ---------------------------------------------------------------------------
# Slice 2 — stress summary
# ---------------------------------------------------------------------------

class TestStressSummary:
    def test_empty_stress_gives_empty_summary(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        card = build_actor_mini_card(_actor(stress={}))
        assert card.stress_summary == []

    def test_single_track_in_summary(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        actor = _actor(stress={"body": _track("body", filled=2, capacity=4)})
        card = build_actor_mini_card(actor)
        assert ("body", 2, 4) in card.stress_summary

    def test_multiple_tracks_all_appear(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        actor = _actor(stress={
            "body": _track("body", filled=1, capacity=4),
            "composure": _track("composure", filled=3, capacity=4),
        })
        card = build_actor_mini_card(actor)
        keys = [t[0] for t in card.stress_summary]
        assert "body" in keys
        assert "composure" in keys

    def test_summary_tuple_has_filled_and_capacity(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        actor = _actor(stress={"weird": _track("weird", filled=2, capacity=4)})
        card = build_actor_mini_card(actor)
        assert card.stress_summary[0] == ("weird", 2, 4)


# ---------------------------------------------------------------------------
# Slice 3 — has_fallout
# ---------------------------------------------------------------------------

class TestHasFallout:
    def test_no_fallout_when_no_tracks_full(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        actor = _actor(stress={"body": _track("body", filled=2, capacity=4)})
        card = build_actor_mini_card(actor)
        assert card.has_fallout is False

    def test_fallout_when_any_track_at_capacity(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        actor = _actor(stress={"body": _track("body", filled=4, capacity=4)})
        card = build_actor_mini_card(actor)
        assert card.has_fallout is True

    def test_fallout_triggered_by_one_full_track_among_many(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        actor = _actor(stress={
            "body": _track("body", filled=1, capacity=4),
            "composure": _track("composure", filled=4, capacity=4),
        })
        card = build_actor_mini_card(actor)
        assert card.has_fallout is True

    def test_no_fallout_with_empty_stress(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        card = build_actor_mini_card(_actor(stress={}))
        assert card.has_fallout is False


# ---------------------------------------------------------------------------
# Slice 4 — portrait_path
# ---------------------------------------------------------------------------

class TestPortraitPath:
    def test_portrait_path_none_without_portraits_dir(self):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        card = build_actor_mini_card(_actor())
        assert card.portrait_path is None

    def test_portrait_path_none_when_file_missing(self, tmp_path):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        card = build_actor_mini_card(_actor(slug="mara"), portraits_dir=tmp_path)
        assert card.portrait_path is None

    def test_portrait_path_resolved_for_png(self, tmp_path):
        from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
        png = tmp_path / "mara.png"
        png.write_bytes(b"")
        card = build_actor_mini_card(_actor(slug="mara"), portraits_dir=tmp_path)
        assert card.portrait_path == png
