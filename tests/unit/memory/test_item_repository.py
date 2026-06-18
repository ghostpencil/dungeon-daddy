from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Item, ItemFeature

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _dungeon_item(
    item_id: str = "item:test:sword",
    campaign_id: str = "campaign:test",
    slug: str = "sword",
    owner_actor_id: str | None = "actor:test:hero",
) -> Item:
    return Item(
        item_id=item_id,
        campaign_id=campaign_id,
        slug=slug,
        display_name="Sword",
        item_type="dungeon_item",
        description="A sharp blade.",
        owner_actor_id=owner_actor_id,
    )


class TestItemMigration:
    def test_migration_creates_items_table(self, repo: MemoryRepository) -> None:
        assert "items" in repo.list_tables()

    def test_migration_creates_item_features_table(self, repo: MemoryRepository) -> None:
        assert "item_features" in repo.list_tables()


class TestSaveAndGetItems:
    def test_round_trip_dungeon_item(self, repo: MemoryRepository) -> None:
        item = _dungeon_item()
        repo.save_item(item)
        results = repo.get_items("campaign:test")
        assert len(results) == 1
        r = results[0]
        assert r["item_id"] == "item:test:sword"
        assert r["slug"] == "sword"
        assert r["display_name"] == "Sword"
        assert r["item_type"] == "dungeon_item"
        assert r["description"] == "A sharp blade."
        assert r["owner_actor_id"] == "actor:test:hero"
        assert r["status"] == "active"
        assert r["features"] == []

    def test_upsert_updates_fields_no_duplicate(self, repo: MemoryRepository) -> None:
        item = _dungeon_item()
        repo.save_item(item)
        updated = item.model_copy(update={"display_name": "Magic Sword"})
        repo.save_item(updated)
        results = repo.get_items("campaign:test")
        assert len(results) == 1
        assert results[0]["display_name"] == "Magic Sword"


class TestGetItemsByActor:
    def test_returns_only_that_actors_items(self, repo: MemoryRepository) -> None:
        hero_item = _dungeon_item(item_id="item:test:sword", slug="sword", owner_actor_id="actor:test:hero")
        rogue_item = _dungeon_item(item_id="item:test:dagger", slug="dagger", owner_actor_id="actor:test:rogue")
        repo.save_item(hero_item)
        repo.save_item(rogue_item)
        results = repo.get_items_by_actor("actor:test:hero")
        assert len(results) == 1
        assert results[0]["item_id"] == "item:test:sword"


class TestFeatures:
    def _gear_item(self) -> Item:
        feature = ItemFeature(
            feature_id="feat:test:1",
            item_id="item:test:gear",
            feature_type="rating_modifier",
            action_key="fight",
            modifier=1,
        )
        return Item(
            item_id="item:test:gear",
            campaign_id="campaign:test",
            slug="chainmail",
            display_name="Chainmail",
            item_type="equipped_gear",
            description="Heavy armour.",
            owner_actor_id="actor:test:hero",
            features=[feature],
        )

    def test_features_nested_in_get_items(self, repo: MemoryRepository) -> None:
        repo.save_item(self._gear_item())
        results = repo.get_items("campaign:test")
        assert len(results[0]["features"]) == 1
        f = results[0]["features"][0]
        assert f["feature_type"] == "rating_modifier"
        assert f["action_key"] == "fight"
        assert f["modifier"] == 1

    def test_upsert_replaces_features(self, repo: MemoryRepository) -> None:
        repo.save_item(self._gear_item())
        new_feature = ItemFeature(
            feature_id="feat:test:2",
            item_id="item:test:gear",
            feature_type="new_action",
            action_key="shield_bash",
            modifier=None,
        )
        updated = self._gear_item().model_copy(update={"features": [new_feature]})
        repo.save_item(updated)
        results = repo.get_items("campaign:test")
        assert len(results[0]["features"]) == 1
        assert results[0]["features"][0]["feature_id"] == "feat:test:2"


class TestItemUpdaters:
    def test_update_item_status(self, repo: MemoryRepository) -> None:
        repo.save_item(_dungeon_item())
        repo.update_item_status("item:test:sword", "consumed")
        result = repo.get_items("campaign:test")[0]
        assert result["status"] == "consumed"

    def test_update_item_charges(self, repo: MemoryRepository) -> None:
        kit = Item(
            item_id="item:test:kit",
            campaign_id="campaign:test",
            slug="lockpick-kit",
            display_name="Lockpick Kit",
            item_type="class_kit",
            description="A set of lockpicks.",
            charges_max=3,
            charges_current=3,
        )
        repo.save_item(kit)
        repo.update_item_charges("item:test:kit", 2)
        result = repo.get_items("campaign:test")[0]
        assert result["charges_current"] == 2

    def test_update_item_equipped(self, repo: MemoryRepository) -> None:
        gear = Item(
            item_id="item:test:ring",
            campaign_id="campaign:test",
            slug="ring",
            display_name="Ring of Power",
            item_type="equipped_gear",
            description="Glows faintly.",
            owner_actor_id="actor:test:hero",
            is_equipped=False,
        )
        repo.save_item(gear)
        repo.update_item_equipped("item:test:ring", True)
        result = repo.get_items("campaign:test")[0]
        assert result["is_equipped"] is True

    def test_update_item_owner(self, repo: MemoryRepository) -> None:
        repo.save_item(_dungeon_item())
        repo.update_item_owner("item:test:sword", "actor:test:rogue")
        result = repo.get_items_by_actor("actor:test:rogue")
        assert len(result) == 1
        assert result[0]["item_id"] == "item:test:sword"
