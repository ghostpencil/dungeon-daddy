from __future__ import annotations

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.models import ContextBundle
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomExit, RoomObject


class TestContextBundleCurrentRoomField:
    def test_context_bundle_has_current_room_field(self) -> None:
        bundle = ContextBundle(
            bundle_id="b1",
            campaign_id="camp_001",
            mode="run_scene",
        )
        assert bundle.current_room == {}


class TestContextBundleCurrentRoomBuilder:
    def test_no_room_id_returns_empty_current_room(
        self, repo: MemoryRepository
    ) -> None:
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)
        assert bundle.current_room == {}

    def test_loose_dungeon_item_in_room_appears_in_loose_items(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_item(Item(
            item_id="item:c1:gold-coin",
            campaign_id="camp_001",
            slug="gold-coin",
            display_name="Gold Coin",
            item_type="dungeon_item",
            description="A shiny coin.",
            room_id="room:level-01:antechamber",
            status="active",
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)

        assert len(bundle.current_room["loose_items"]) == 1
        item = bundle.current_room["loose_items"][0]
        assert item["item_id"] == "item:c1:gold-coin"
        assert item["slug"] == "gold-coin"
        assert item["display_name"] == "Gold Coin"
        assert item["description"] == "A shiny coin."
        assert item["status"] == "active"

    def test_owned_item_excluded_from_loose_items(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_item(Item(
            item_id="item:c1:dagger",
            campaign_id="camp_001",
            slug="dagger",
            display_name="Dagger",
            item_type="dungeon_item",
            description="A short blade.",
            owner_actor_id="actor:c1:mara",
            room_id=None,
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)

        assert bundle.current_room["loose_items"] == []

    def test_object_in_room_appears_in_objects_with_correct_fields(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_room_object(RoomObject(
            object_id="obj:c1:iron-chest",
            campaign_id="camp_001",
            room_id="room:level-01:antechamber",
            level_id="level-01",
            slug="iron-chest",
            display_name="Iron Chest",
            archetype="container",
            description="A heavy iron chest.",
            current_state="sealed",
            transitions=[
                ObjectTransition(
                    transition_id="tr:c1:iron-chest:0",
                    object_id="obj:c1:iron-chest",
                    from_state="sealed",
                    to_state="opened",
                    trigger="open",
                )
            ],
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)

        assert len(bundle.current_room["objects"]) == 1
        obj = bundle.current_room["objects"][0]
        assert obj["object_id"] == "obj:c1:iron-chest"
        assert obj["slug"] == "iron-chest"
        assert obj["display_name"] == "Iron Chest"
        assert obj["archetype"] == "container"
        assert obj["current_state"] == "sealed"
        assert obj["description"] == "A heavy iron chest."
        assert "transitions" not in obj

    def test_obstacle_object_carries_approach_verbs(
        self, repo: MemoryRepository
    ) -> None:
        # Phase 51.5 Part A Slice 3: an obstacle's contested approaches surface as
        # `approach_verbs` on its context object dict so the builder can suggest
        # them; raw transitions stay off the thin view-model.
        from dungeon_daddy.memory.context_bundle import build_room_noun_context

        room_id = "room:level-01:antechamber"
        repo.save_room_object(RoomObject(
            object_id="obj:c1:gearworks",
            campaign_id="camp_001",
            room_id=room_id,
            level_id="level-01",
            slug="gearworks",
            display_name="Seized Gearworks",
            archetype="mechanism",
            description="A jammed tangle of brass gears.",
            current_state="jammed",
            transitions=[
                ObjectTransition(
                    transition_id="tr:c1:gearworks:tinker",
                    object_id="obj:c1:gearworks",
                    from_state="jammed", to_state="cleared", trigger="tinker",
                    contested=True, action_verb="tinker",
                ),
                ObjectTransition(
                    transition_id="tr:c1:gearworks:fight",
                    object_id="obj:c1:gearworks",
                    from_state="jammed", to_state="cleared", trigger="fight",
                    contested=True, action_verb="fight",
                ),
            ],
        ))

        ctx = build_room_noun_context(repo, "camp_001", room_id)
        obj = ctx["objects"][0]
        # Order follows the repo's transition_id sort (fight < tinker), which the
        # seed controls via authored ids.
        assert obj["approach_verbs"] == ["fight", "tinker"]
        assert "transitions" not in obj

    def test_non_obstacle_object_has_empty_approach_verbs(
        self, repo: MemoryRepository
    ) -> None:
        from dungeon_daddy.memory.context_bundle import build_room_noun_context

        room_id = "room:level-01:antechamber"
        repo.save_room_object(RoomObject(
            object_id="obj:c1:iron-chest",
            campaign_id="camp_001",
            room_id=room_id,
            level_id="level-01",
            slug="iron-chest",
            display_name="Iron Chest",
            archetype="container",
            description="A heavy iron chest.",
            current_state="sealed",
            transitions=[
                ObjectTransition(
                    transition_id="tr:c1:iron-chest:0",
                    object_id="obj:c1:iron-chest",
                    from_state="sealed", to_state="opened", trigger="open",
                )
            ],
        ))

        ctx = build_room_noun_context(repo, "camp_001", room_id)
        assert ctx["objects"][0]["approach_verbs"] == []

    def test_resonance_point_object_sets_room_flag(
        self, repo: MemoryRepository
    ) -> None:
        # Phase 51: build_room_noun_context derives the resonance_point flag so the
        # Play-mode dungeon-channel gate (dungeon_channel_available) can read it
        # from the same context the VNA panel uses.
        from dungeon_daddy.memory.context_bundle import build_room_noun_context

        room_id = "room:level-01:antechamber"
        repo.save_room_object(RoomObject(
            object_id="obj:c1:node",
            campaign_id="camp_001",
            room_id=room_id,
            level_id="level-01",
            slug="resonance-node",
            display_name="Resonance Node",
            archetype="resonance_point",
            description="A node where the dungeon's mind presses close.",
            current_state="attuned",
            transitions=[],
        ))

        ctx = build_room_noun_context(repo, "camp_001", room_id)
        assert ctx["resonance_point"] is True

    def test_no_resonance_point_object_leaves_flag_false(
        self, repo: MemoryRepository
    ) -> None:
        from dungeon_daddy.memory.context_bundle import build_room_noun_context

        ctx = build_room_noun_context(repo, "camp_001", "room:level-01:antechamber")
        assert ctx["resonance_point"] is False

    def test_room_id_with_no_contents_returns_empty_lists(
        self, repo: MemoryRepository
    ) -> None:
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)
        assert bundle.current_room == {
            "room_id": "room:level-01:antechamber",
            "resonance_point": False,
            "objects": [],
            "loose_items": [],
            "npcs": [],
            "monsters": [],
            "exits": [],
        }

    def test_npc_in_room_appears_in_npcs(self, repo: MemoryRepository) -> None:
        repo.save_actor(
            "actor:c1:warden", "camp_001", "npc", "warden", "The Warden", "active",
            room_id="room:level-01:antechamber",
        )
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)
        assert bundle.current_room["npcs"] == [
            {
                "actor_id": "actor:c1:warden",
                "slug": "warden",
                "display_name": "The Warden",
                "status": "active",
                "disposition": "neutral",
            }
        ]
        assert bundle.current_room["monsters"] == []

    def test_npc_disposition_surfaces_in_room_context(
        self, repo: MemoryRepository
    ) -> None:
        # A willing NPC carries its disposition into the room context so the
        # dialogue gate (is_speakable) can open the SAY box (Phase 50.6 §6).
        repo.save_actor(
            "actor:c1:pinion", "camp_001", "npc", "pinion", "Pinion", "active",
            room_id="room:level-01:antechamber", disposition="willing",
        )
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)
        assert bundle.current_room["npcs"][0]["disposition"] == "willing"

    def test_willing_npc_is_speakable_end_to_end(
        self, repo: MemoryRepository
    ) -> None:
        # Full data path: a willing NPC saved in the repo flows through
        # build_room_noun_context → available_nouns → is_speakable, so the
        # builder's dialogue gate opens for it (Phase 50.6 §6).
        from dungeon_daddy.memory.context_bundle import build_room_noun_context
        from dungeon_daddy.rpg.action_options import available_nouns, is_speakable

        room_id = "room:level-01:antechamber"
        repo.save_actor(
            "actor:c1:pinion", "camp_001", "npc", "pinion", "Pinion", "active",
            room_id=room_id, disposition="willing",
        )
        room_context = build_room_noun_context(repo, "camp_001", room_id)
        actor = {"actor_id": "actor:c1:hero", "display_name": "Hero", "carried_items": []}
        pinion = next(
            n for n in available_nouns(room_context, actor)
            if n.noun_id == "actor:c1:pinion"
        )
        assert is_speakable(pinion, room_context) is True

    def test_monster_in_room_appears_in_monsters(self, repo: MemoryRepository) -> None:
        repo.save_actor(
            "actor:c1:ghoul", "camp_001", "monster", "ghoul", "Pale Ghoul", "active",
            room_id="room:level-01:antechamber",
        )
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)
        assert bundle.current_room["monsters"] == [
            {
                "actor_id": "actor:c1:ghoul",
                "slug": "ghoul",
                "display_name": "Pale Ghoul",
                "status": "active",
                "disposition": "neutral",
            }
        ]
        assert bundle.current_room["npcs"] == []

    def test_actor_in_other_room_excluded(self, repo: MemoryRepository) -> None:
        repo.save_actor(
            "actor:c1:elsewhere", "camp_001", "npc", "elsewhere", "Elsewhere", "active",
            room_id="room:level-01:vault",
        )
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)
        assert bundle.current_room["npcs"] == []

    def test_exit_from_room_appears_in_exits(self, repo: MemoryRepository) -> None:
        repo.save_room_exit(RoomExit(
            exit_id="exit:c1:north",
            campaign_id="camp_001",
            from_room_id="room:level-01:antechamber",
            to_room_id="room:level-01:vault",
            level_id="level-01",
            label="North Door",
            status="open",
        ))
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
            current_room_id="room:level-01:antechamber",
        ).build(repo)
        assert bundle.current_room["exits"] == [
            {
                "exit_id": "exit:c1:north",
                "label": "North Door",
                "status": "open",
                "to_room_id": "room:level-01:vault",
            }
        ]
