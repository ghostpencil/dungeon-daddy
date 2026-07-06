import pytest
from pydantic import ValidationError

from dungeon_daddy.rpg.models import (
    CLOCK_CATEGORIES,
    ActionRating,
    ActionRequest,
    ActionResolution,
    ActorState,
    ClockCategory,
    ClockState,
    FalloutRecord,
    Item,
    ItemFeature,
    Objective,
    ObjectiveCompletion,
    ObjectReactionBinding,
    ObjectTransition,
    ReactionClockLine,
    ReactionStressLine,
    RoomExit,
    RoomObject,
    StressTrack,
    WorldReaction,
    is_adverse,
    is_known_clock_category,
    normalize_clock_category,
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

    def test_room_id_defaults_to_none_and_accepts_value(self) -> None:
        a = ActorState(
            actor_id="x", campaign_id="c", actor_type="npc", slug="s", display_name="D"
        )
        assert a.room_id is None
        b = ActorState(
            actor_id="y", campaign_id="c", actor_type="monster", slug="s2",
            display_name="D2", room_id="room:level-01:antechamber",
        )
        assert b.room_id == "room:level-01:antechamber"

    def test_disposition_defaults_to_neutral_and_accepts_willing(self) -> None:
        a = ActorState(
            actor_id="x", campaign_id="c", actor_type="npc", slug="s", display_name="D"
        )
        assert a.disposition == "neutral"
        b = ActorState(
            actor_id="y", campaign_id="c", actor_type="npc", slug="s2",
            display_name="D2", disposition="willing",
        )
        assert b.disposition == "willing"

    def test_invalid_disposition_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ActorState(
                actor_id="x", campaign_id="c", actor_type="npc", slug="s",
                display_name="D", disposition="ecstatic",
            )

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

    def test_monotonic_defaults_to_true(self) -> None:
        c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4)
        assert c.monotonic is True

    def test_monotonic_can_be_set_false(self) -> None:
        c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4, monotonic=False)
        assert c.monotonic is False

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

    def test_category_accepts_and_round_trips_a_clock_category(self) -> None:
        c = ClockState(
            clock_id="c", campaign_id="x", label="L", segments=4, category="danger"
        )
        assert c.category == "danger"
        assert ClockState.model_validate(c.model_dump()).category == "danger"

    def test_category_preserves_unknown_string_for_back_compat(self) -> None:
        # Live/seeded clocks carry categories not yet in the enum (e.g. "threat",
        # "escalation", "environment"); Slice 2 normalizes them. Loading must not crash.
        c = ClockState(
            clock_id="c", campaign_id="x", label="L", segments=4, category="threat"
        )
        assert c.category == "threat"

    def test_optional_level_metadata_defaults(self) -> None:
        c = ClockState(clock_id="c", campaign_id="x", label="L", segments=4)
        assert c.category is None
        assert c.level_id is None
        assert c.owner_actor_id is None
        assert c.stakes is None
        assert c.completion_effect is None
        assert c.visible_to_player is True


class TestIsAdverse:
    def test_danger_pursuit_ritual_are_adverse(self) -> None:
        assert is_adverse("danger") is True
        assert is_adverse("pursuit") is True
        assert is_adverse("ritual") is True

    def test_firewalled_categories_are_not_adverse(self) -> None:
        firewalled: tuple[ClockCategory, ...] = (
            "objective", "relationship", "faction_pressure", "dungeon_intimacy",
        )
        for cat in firewalled:
            assert is_adverse(cat) is False

    def test_none_is_not_adverse(self) -> None:
        assert is_adverse(None) is False

    def test_raw_synonyms_must_be_normalized_before_asking(self) -> None:
        # is_adverse takes a normalized ClockCategory (the narrowed signature
        # makes passing a raw string a type error). A synonym like "threat" is
        # adverse only *after* normalization maps it onto danger; an unknown
        # category normalizes to the non-adverse faction_pressure fallback.
        assert is_adverse(normalize_clock_category("threat")) is True
        assert is_adverse(normalize_clock_category("mystery-category")) is False


class TestNormalizeClockCategory:
    def test_none_stays_none(self) -> None:
        assert normalize_clock_category(None) is None

    def test_canonical_members_pass_through_unchanged(self) -> None:
        for cat in CLOCK_CATEGORIES:
            assert normalize_clock_category(cat) == cat

    def test_is_idempotent(self) -> None:
        for cat in (None, "danger", "threat", "environment", "escalation", "mystery"):
            once = normalize_clock_category(cat)
            assert normalize_clock_category(once) == once

    def test_known_synonyms_map_to_canonical_members(self) -> None:
        assert normalize_clock_category("threat") == "danger"
        assert normalize_clock_category("environment") == "danger"
        assert normalize_clock_category("escalation") == "pursuit"

    def test_unknown_string_falls_back_to_a_protected_non_adverse_member(self) -> None:
        result = normalize_clock_category("mystery-category")
        assert result in CLOCK_CATEGORIES
        # Fail-safe: an unrecognized clock must never become ambient-eligible.
        assert is_adverse(result) is False

    def test_every_normalized_result_is_a_valid_enum_member(self) -> None:
        for raw in (None, "danger", "threat", "environment", "escalation", "???"):
            result = normalize_clock_category(raw)
            assert result is None or result in CLOCK_CATEGORIES


class TestIsKnownClockCategory:
    def test_canonical_members_and_known_synonyms_are_known(self) -> None:
        for cat in (*CLOCK_CATEGORIES, "threat", "environment", "escalation"):
            assert is_known_clock_category(cat) is True

    def test_none_is_known(self) -> None:
        assert is_known_clock_category(None) is True

    def test_unrecognized_string_is_not_known(self) -> None:
        # This is the "explicit, not silent" signal: a data pass can flag the
        # clock instead of coercing it invisibly.
        assert is_known_clock_category("mystery-category") is False


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


class TestItem:
    def test_constructs_with_required_fields(self) -> None:
        item = Item(
            item_id="item:camp-1:torch",
            campaign_id="camp-1",
            slug="torch",
            display_name="Torch",
            item_type="dungeon_item",
            description="A simple torch that lights the way.",
        )
        assert item.item_id == "item:camp-1:torch"
        assert item.status == "active"
        assert item.is_equipped is False
        assert item.features == []

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Item(
                item_id="item:c:x",
                campaign_id="c",
                slug="x",
                display_name="X",
                item_type="dungeon_item",
                description="",
            )

    def test_class_kit_requires_charges_max(self) -> None:
        with pytest.raises(ValidationError):
            Item(
                item_id="item:c:kit",
                campaign_id="c",
                slug="kit",
                display_name="Kit",
                item_type="class_kit",
                description="A healer kit.",
                charges_max=0,
                charges_current=0,
            )

    def test_class_kit_charges_current_cannot_exceed_max(self) -> None:
        with pytest.raises(ValidationError):
            Item(
                item_id="item:c:kit",
                campaign_id="c",
                slug="kit",
                display_name="Kit",
                item_type="class_kit",
                description="A healer kit.",
                charges_max=3,
                charges_current=4,
            )

    def test_dungeon_item_cannot_carry_features(self) -> None:
        with pytest.raises(ValidationError):
            Item(
                item_id="item:c:stone",
                campaign_id="c",
                slug="stone",
                display_name="Stone",
                item_type="dungeon_item",
                description="A magic stone.",
                features=[
                    ItemFeature(
                        feature_id="f1",
                        item_id="item:c:stone",
                        feature_type="new_action",
                        action_key="throw",
                    )
                ],
            )

    def test_equipped_gear_accepts_features(self) -> None:
        item = Item(
            item_id="item:c:sword",
            campaign_id="c",
            slug="sword",
            display_name="Sword",
            item_type="equipped_gear",
            description="A sharp blade.",
            features=[
                ItemFeature(
                    feature_id="f1",
                    item_id="item:c:sword",
                    feature_type="rating_modifier",
                    action_key="fight",
                    modifier=1,
                )
            ],
        )
        assert len(item.features) == 1

    def test_room_id_defaults_to_none(self) -> None:
        item = Item(
            item_id="item:c:torch",
            campaign_id="c",
            slug="torch",
            display_name="Torch",
            item_type="dungeon_item",
            description="A flickering torch.",
        )
        assert item.room_id is None

    def test_room_id_can_be_set(self) -> None:
        item = Item(
            item_id="item:c:torch",
            campaign_id="c",
            slug="torch",
            display_name="Torch",
            item_type="dungeon_item",
            description="A flickering torch.",
            room_id="room:entrance",
        )
        assert item.room_id == "room:entrance"


class TestItemFeature:
    def test_rating_modifier_requires_modifier(self) -> None:
        with pytest.raises(ValidationError):
            ItemFeature(
                feature_id="f1",
                item_id="item:c:sword",
                feature_type="rating_modifier",
                action_key="fight",
                modifier=None,
            )

    def test_new_action_requires_modifier_none(self) -> None:
        with pytest.raises(ValidationError):
            ItemFeature(
                feature_id="f1",
                item_id="item:c:sword",
                feature_type="new_action",
                action_key="cleave",
                modifier=1,
            )


class TestRoomObject:
    def test_constructs_with_required_fields(self) -> None:
        obj = RoomObject(
            object_id="obj:camp-1:chest",
            campaign_id="camp-1",
            room_id="room:entrance",
            level_id="level:1",
            slug="chest",
            display_name="Iron Chest",
            archetype="container",
            description="A heavy iron chest.",
            current_state="sealed",
        )
        assert obj.object_id == "obj:camp-1:chest"
        assert obj.archetype == "container"
        assert obj.transitions == []

    def test_all_archetypes_accepted(self) -> None:
        for archetype in ("container", "door", "mechanism", "structure", "trap", "lore_fixture", "resource"):
            obj = RoomObject(
                object_id="obj:c:x",
                campaign_id="c",
                room_id="room:r",
                level_id="level:1",
                slug="x",
                display_name="X",
                archetype=archetype,
                description="Some fixture.",
                current_state="sealed",
            )
            assert obj.archetype == archetype

    def test_resonance_point_archetype_accepted(self) -> None:
        obj = RoomObject(
            object_id="obj:c:font",
            campaign_id="c",
            room_id="room:r",
            level_id="level:1",
            slug="resonance-font",
            display_name="Humming Font",
            archetype="resonance_point",
            description="A font that hums when you draw near.",
            current_state="dormant",
        )
        assert obj.archetype == "resonance_point"

    def test_unknown_archetype_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RoomObject(
                object_id="obj:c:x",
                campaign_id="c",
                room_id="room:r",
                level_id="level:1",
                slug="x",
                display_name="X",
                archetype="cursed_idol",
                description="An idol.",
                current_state="intact",
            )

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RoomObject(
                object_id="obj:c:x",
                campaign_id="c",
                room_id="room:r",
                level_id="level:1",
                slug="x",
                display_name="X",
                archetype="trap",
                description="   ",
                current_state="armed",
            )


class TestObjectTransition:
    def test_constructs_with_required_fields_optional_defaults_none(self) -> None:
        t = ObjectTransition(
            transition_id="tr:1",
            object_id="obj:c:chest",
            from_state="sealed",
            to_state="opened",
            trigger="open",
        )
        assert t.transition_id == "tr:1"
        assert t.requires_item_slug is None
        assert t.spawns_item_slug is None
        assert t.advances_clock_slug is None

    def test_optional_effect_slugs_stored(self) -> None:
        t = ObjectTransition(
            transition_id="tr:2",
            object_id="obj:c:chest",
            from_state="locked",
            to_state="unlocked",
            trigger="unlock",
            requires_item_slug="iron-key",
            spawns_item_slug="gold-coin",
            advances_clock_slug="ritual-clock",
        )
        assert t.requires_item_slug == "iron-key"
        assert t.spawns_item_slug == "gold-coin"
        assert t.advances_clock_slug == "ritual-clock"

    def test_contested_defaults_to_false_and_action_verb_defaults_to_none(self) -> None:
        t = ObjectTransition(
            transition_id="tr:3",
            object_id="obj:c:chest",
            from_state="sealed",
            to_state="opened",
            trigger="open",
        )
        assert t.contested is False
        assert t.action_verb is None

    def test_contested_flag_and_action_verb_stored(self) -> None:
        t = ObjectTransition(
            transition_id="tr:4",
            object_id="obj:c:mechanism",
            from_state="idle",
            to_state="triggered",
            trigger="operate",
            contested=True,
            action_verb="scrap",
        )
        assert t.contested is True
        assert t.action_verb == "scrap"


class TestRoomObjectReactionPolicy:
    def _obj(self, **overrides: object) -> RoomObject:
        kwargs: dict[str, object] = dict(
            object_id="obj:c:statue",
            campaign_id="c",
            room_id="room:r1",
            level_id="level:1",
            slug="statue",
            display_name="Toppled Artificer Statue",
            archetype="lore_fixture",
            description="A toppled statue of the artificer.",
            current_state="intact",
        )
        kwargs.update(overrides)
        return RoomObject(**kwargs)  # type: ignore[arg-type]

    def test_reaction_policy_defaults_to_ambient(self) -> None:
        obj = self._obj()
        assert obj.reaction_policy == "ambient"

    def test_reaction_bindings_default_empty(self) -> None:
        obj = self._obj()
        assert obj.reaction_bindings == []

    def test_all_reaction_policies_accepted(self) -> None:
        for policy in ("scripted", "ambient", "inert"):
            obj = self._obj(reaction_policy=policy)
            assert obj.reaction_policy == policy

    def test_unknown_reaction_policy_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._obj(reaction_policy="chaotic")

    def test_round_trip_preserves_policy_and_bindings(self) -> None:
        obj = self._obj(
            reaction_policy="scripted",
            reaction_bindings=[
                ObjectReactionBinding(
                    binding_id="rb:1",
                    object_id="obj:c:statue",
                    action_verb="study",
                    outcome="miss",
                    clock_slug="scorpion-nest-agitated",
                    clock_delta=1,
                )
            ],
        )
        restored = RoomObject.model_validate(obj.model_dump())
        assert restored.reaction_policy == "scripted"
        assert len(restored.reaction_bindings) == 1
        assert restored.reaction_bindings[0].binding_id == "rb:1"
        assert restored.reaction_bindings[0].clock_slug == "scorpion-nest-agitated"


class TestObjectReactionBinding:
    def test_constructs_with_required_fields_optional_defaults(self) -> None:
        b = ObjectReactionBinding(
            binding_id="rb:1",
            object_id="obj:c:statue",
            action_verb="study",
            outcome="miss",
        )
        assert b.binding_id == "rb:1"
        assert b.action_verb == "study"
        assert b.outcome == "miss"
        assert b.clock_slug is None
        assert b.clock_delta == 0
        assert b.stress_track is None
        assert b.stress_amount == 0

    def test_wildcard_verb_accepted(self) -> None:
        b = ObjectReactionBinding(
            binding_id="rb:2",
            object_id="obj:c:statue",
            action_verb="*",
            outcome="partial",
        )
        assert b.action_verb == "*"

    def test_both_outcome_tiers_accepted(self) -> None:
        for outcome in ("miss", "partial"):
            b = ObjectReactionBinding(
                binding_id="rb:x",
                object_id="obj:c:statue",
                action_verb="study",
                outcome=outcome,
            )
            assert b.outcome == outcome

    def test_unknown_outcome_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObjectReactionBinding(
                binding_id="rb:3",
                object_id="obj:c:statue",
                action_verb="study",
                outcome="success",
            )

    def test_clock_and_stress_consequences_stored(self) -> None:
        b = ObjectReactionBinding(
            binding_id="rb:4",
            object_id="obj:c:statue",
            action_verb="force",
            outcome="miss",
            clock_slug="scorpion-nest-agitated",
            clock_delta=2,
            stress_track="body",
            stress_amount=1,
        )
        assert b.clock_slug == "scorpion-nest-agitated"
        assert b.clock_delta == 2
        assert b.stress_track == "body"
        assert b.stress_amount == 1

    def test_round_trip(self) -> None:
        b = ObjectReactionBinding(
            binding_id="rb:5",
            object_id="obj:c:statue",
            action_verb="*",
            outcome="partial",
            clock_slug="the-factory-learns",
            clock_delta=1,
        )
        restored = ObjectReactionBinding.model_validate(b.model_dump())
        assert restored == b

    def test_clock_slug_without_delta_rejected(self) -> None:
        # Silent-no-op guard: a slug with a zero delta matches a verb/outcome
        # and then advances nothing — reject it at authoring time.
        with pytest.raises(ValidationError):
            ObjectReactionBinding(
                binding_id="rb:6", object_id="obj:c:statue",
                action_verb="study", outcome="miss",
                clock_slug="scorpion-nest-agitated", clock_delta=0,
            )

    def test_clock_delta_without_slug_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObjectReactionBinding(
                binding_id="rb:7", object_id="obj:c:statue",
                action_verb="study", outcome="miss",
                clock_delta=2,
            )

    def test_stress_track_without_amount_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObjectReactionBinding(
                binding_id="rb:8", object_id="obj:c:statue",
                action_verb="study", outcome="miss",
                stress_track="body", stress_amount=0,
            )

    def test_stress_amount_without_track_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObjectReactionBinding(
                binding_id="rb:9", object_id="obj:c:statue",
                action_verb="study", outcome="miss",
                stress_amount=2,
            )


class TestRoomExit:
    def test_constructs_with_required_fields_and_defaults(self) -> None:
        exit_ = RoomExit(
            exit_id="exit:c:r1:r2",
            campaign_id="camp-1",
            from_room_id="room:entrance",
            to_room_id="room:corridor",
            level_id="level:1",
            label="North Door",
        )
        assert exit_.exit_id == "exit:c:r1:r2"
        assert exit_.exit_type == "door"
        assert exit_.connector_type is None
        assert exit_.status == "open"
        assert exit_.requires_item_slug is None
        assert exit_.requires_object_id is None
        assert exit_.requires_object_state is None
        assert exit_.requires_clock_slug is None
        assert exit_.requires_clock_min_filled is None
        assert exit_.requires_memory_slug is None

    def test_all_condition_fields_stored(self) -> None:
        exit_ = RoomExit(
            exit_id="exit:c:r1:r3",
            campaign_id="camp-1",
            from_room_id="room:entrance",
            to_room_id="room:vault",
            level_id="level:1",
            label="Spiral Stair",
            status="locked",
            requires_item_slug="iron-key",
            requires_object_id="obj:c:lever",
            requires_object_state="pulled",
            requires_clock_slug="ritual-clock",
            requires_clock_min_filled=3,
            requires_memory_slug="found-the-passage",
        )
        assert exit_.status == "locked"
        assert exit_.requires_item_slug == "iron-key"
        assert exit_.requires_object_id == "obj:c:lever"
        assert exit_.requires_object_state == "pulled"
        assert exit_.requires_clock_slug == "ritual-clock"
        assert exit_.requires_clock_min_filled == 3
        assert exit_.requires_memory_slug == "found-the-passage"

    def test_connector_type_can_be_set(self) -> None:
        exit_ = RoomExit(
            exit_id="exit:c:r1:r4",
            campaign_id="camp-1",
            from_room_id="room:level1-bottom",
            to_room_id="room:level2-top",
            level_id="level:1",
            label="Spiral Stair Down",
            connector_type="stair_down",
        )
        assert exit_.connector_type == "stair_down"


class TestObjectiveCompletion:
    def test_object_state_completion_constructs(self) -> None:
        c = ObjectiveCompletion(
            kind="object_state",
            target_slug="coolant-loop",
            required_state="restored",
        )
        assert c.kind == "object_state"
        assert c.target_slug == "coolant-loop"
        assert c.required_state == "restored"

    def test_object_state_requires_required_state(self) -> None:
        with pytest.raises(ValidationError):
            ObjectiveCompletion(kind="object_state", target_slug="coolant-loop")

    def test_item_obtained_completion_needs_no_required_state(self) -> None:
        c = ObjectiveCompletion(kind="item_obtained", target_slug="resonance-key")
        assert c.required_state is None

    def test_unknown_kind_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObjectiveCompletion(kind="vibes_aligned", target_slug="x")


class TestObjective:
    def _completion(self) -> ObjectiveCompletion:
        return ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )

    def test_constructs_with_required_fields_and_defaults(self) -> None:
        obj = Objective(
            objective_id="obj:camp-1:restore-coolant",
            campaign_id="camp-1",
            slug="restore-coolant",
            title="Restore the Coolant Loop",
            description="The Crucible wants its coolant loop online again.",
            tier_index=0,
            completion=self._completion(),
        )
        assert obj.status == "locked"
        assert obj.advances_clock_slug is None
        assert obj.reveals_knowledge == []
        assert obj.completion.target_slug == "coolant-loop"

    def test_full_fields_stored(self) -> None:
        obj = Objective(
            objective_id="obj:camp-1:restore-core",
            campaign_id="camp-1",
            slug="restore-core",
            title="Restore the Memory Core",
            description="Bring the core back so the dungeon can remember.",
            tier_index=2,
            status="active",
            completion=self._completion(),
            advances_clock_slug="dungeon_intimacy",
            reveals_knowledge=["The core holds the forge-mind's true name."],
        )
        assert obj.status == "active"
        assert obj.advances_clock_slug == "dungeon_intimacy"
        assert obj.reveals_knowledge == ["The core holds the forge-mind's true name."]

    def test_unknown_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Objective(
                objective_id="o",
                campaign_id="c",
                slug="s",
                title="T",
                description="D",
                tier_index=0,
                status="smitten",
                completion=self._completion(),
            )

    def test_negative_tier_index_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Objective(
                objective_id="o",
                campaign_id="c",
                slug="s",
                title="T",
                description="D",
                tier_index=-1,
                completion=self._completion(),
            )
