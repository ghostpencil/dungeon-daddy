from __future__ import annotations

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.models import ContextBundle
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Item, ItemFeature


class TestContextBundleInventoryField:
    def test_context_bundle_has_inventory_field(self) -> None:
        bundle = ContextBundle(
            bundle_id="b1",
            campaign_id="camp_001",
            mode="run_scene",
        )
        assert bundle.inventory == {}


class TestContextBundleInventoryBuilder:
    def test_build_returns_empty_inventory_when_no_focus_actors(
        self, repo: MemoryRepository
    ) -> None:
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)
        assert bundle.inventory == {}

    def test_focus_actor_kit_appears_in_kits(self, repo: MemoryRepository) -> None:
        repo.save_item(Item(
            item_id="item:c1:lockpicks",
            campaign_id="camp_001",
            slug="lockpicks",
            display_name="Lockpicks",
            item_type="class_kit",
            description="A set of picks.",
            owner_actor_id="actor:c1:mara",
            charges_current=3,
            charges_max=3,
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor:c1:mara"],
            token_budget=500,
        ).build(repo)

        actor_inv = bundle.inventory["actor:c1:mara"]
        assert len(actor_inv["kits"]) == 1
        kit = actor_inv["kits"][0]
        assert kit["slug"] == "lockpicks"
        assert kit["display_name"] == "Lockpicks"
        assert kit["charges_current"] == 3
        assert kit["charges_max"] == 3

    def test_dungeon_item_appears_with_level_bound_flag(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_item(Item(
            item_id="item:c1:ancient-key",
            campaign_id="camp_001",
            slug="ancient-key",
            display_name="Ancient Key",
            item_type="dungeon_item",
            description="Opens the vault.",
            owner_actor_id="actor:c1:mara",
            level_id="level-01",
        ))
        repo.save_item(Item(
            item_id="item:c1:torch",
            campaign_id="camp_001",
            slug="torch",
            display_name="Torch",
            item_type="dungeon_item",
            description="Lights the way.",
            owner_actor_id="actor:c1:mara",
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor:c1:mara"],
            token_budget=500,
        ).build(repo)

        dungeon_items = bundle.inventory["actor:c1:mara"]["dungeon_items"]
        assert len(dungeon_items) == 2
        key = next(d for d in dungeon_items if d["slug"] == "ancient-key")
        torch = next(d for d in dungeon_items if d["slug"] == "torch")
        assert key["level_bound"] is True
        assert torch["level_bound"] is False
        assert key["description"] == "Opens the vault."
        assert key["status"] == "active"

    def test_equipped_gear_with_features_appears_in_equipped(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_item(Item(
            item_id="item:c1:sword",
            campaign_id="camp_001",
            slug="sword",
            display_name="Iron Sword",
            item_type="equipped_gear",
            description="A reliable blade.",
            owner_actor_id="actor:c1:mara",
            is_equipped=True,
            features=[
                ItemFeature(
                    feature_id="feat:c1:sword-fight",
                    item_id="item:c1:sword",
                    feature_type="rating_modifier",
                    action_key="fight",
                    modifier=1,
                )
            ],
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor:c1:mara"],
            token_budget=500,
        ).build(repo)

        equipped = bundle.inventory["actor:c1:mara"]["equipped"]
        assert len(equipped) == 1
        gear = equipped[0]
        assert gear["slug"] == "sword"
        assert gear["display_name"] == "Iron Sword"
        assert len(gear["features"]) == 1
        assert gear["features"][0]["action_key"] == "fight"
        assert gear["features"][0]["modifier"] == 1

    def test_effective_actions_adds_equipped_modifier_to_base_rating(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_actor("actor:c1:mara", "camp_001", "pc", "mara", "Mara")
        repo.save_actor_action_rating("actor:c1:mara", "fight", 2)
        repo.save_item(Item(
            item_id="item:c1:sword",
            campaign_id="camp_001",
            slug="sword",
            display_name="Iron Sword",
            item_type="equipped_gear",
            description="A reliable blade.",
            owner_actor_id="actor:c1:mara",
            is_equipped=True,
            features=[
                ItemFeature(
                    feature_id="feat:c1:sword-fight",
                    item_id="item:c1:sword",
                    feature_type="rating_modifier",
                    action_key="fight",
                    modifier=1,
                )
            ],
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor:c1:mara"],
            token_budget=500,
        ).build(repo)

        effective = bundle.inventory["actor:c1:mara"]["effective_actions"]
        assert effective["fight"] == 3

    def test_non_focus_actor_excluded_from_inventory(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_item(Item(
            item_id="item:c1:lockpicks",
            campaign_id="camp_001",
            slug="lockpicks",
            display_name="Lockpicks",
            item_type="class_kit",
            description="A set of picks.",
            owner_actor_id="actor:c1:bystander",
            charges_current=2,
            charges_max=2,
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=["actor:c1:mara"],
            token_budget=500,
        ).build(repo)

        assert "actor:c1:bystander" not in bundle.inventory
