from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Objective, ObjectiveCompletion

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


def _objective(
    objective_id: str = "obj:test:coolant",
    campaign_id: str = "campaign:test",
    slug: str = "restore-coolant-loop",
    tier_index: int = 0,
    status: str = "active",
    required_state: str = "restored",
    reveals_knowledge: list[str] | None = None,
) -> Objective:
    return Objective(
        objective_id=objective_id,
        campaign_id=campaign_id,
        slug=slug,
        title="Restore the Coolant Loop",
        description="The dungeon wants its coolant loop restored.",
        tier_index=tier_index,
        status=status,
        completion=ObjectiveCompletion(
            kind="object_state",
            target_slug="coolant-valve",
            required_state=required_state,
        ),
        advances_clock_slug="dungeon_intimacy",
        reveals_knowledge=reveals_knowledge if reveals_knowledge is not None else [],
    )


class TestRoundTrip:
    def test_save_and_get_basic_fields(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective())
        results = repo.get_objectives("campaign:test")
        assert len(results) == 1
        o = results[0]
        assert o["objective_id"] == "obj:test:coolant"
        assert o["campaign_id"] == "campaign:test"
        assert o["slug"] == "restore-coolant-loop"
        assert o["title"] == "Restore the Coolant Loop"
        assert o["description"] == "The dungeon wants its coolant loop restored."
        assert o["tier_index"] == 0
        assert o["status"] == "active"
        assert o["advances_clock_slug"] == "dungeon_intimacy"

    def test_completion_round_trips(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective())
        o = repo.get_objectives("campaign:test")[0]
        assert o["completion"] == {
            "kind": "object_state",
            "target_slug": "coolant-valve",
            "required_state": "restored",
        }

    def test_reveals_knowledge_round_trips_in_order(self, repo: MemoryRepository) -> None:
        secrets = ["The forge-mind never forgets.", "Coolant feeds the deep vault."]
        repo.save_objective(_objective(reveals_knowledge=secrets))
        o = repo.get_objectives("campaign:test")[0]
        assert o["reveals_knowledge"] == secrets

    def test_empty_reveals_knowledge_is_empty_list(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective())
        o = repo.get_objectives("campaign:test")[0]
        assert o["reveals_knowledge"] == []


class TestUpdateStatus:
    def test_update_objective_status(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective(status="active"))
        repo.update_objective_status("obj:test:coolant", "completed")
        o = repo.get_objectives("campaign:test")[0]
        assert o["status"] == "completed"


class TestGetObjectives:
    def test_filters_by_campaign(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective(objective_id="obj:a:1", campaign_id="campaign:a", slug="a1"))
        repo.save_objective(_objective(objective_id="obj:b:1", campaign_id="campaign:b", slug="b1"))
        results = repo.get_objectives("campaign:a")
        assert len(results) == 1
        assert results[0]["objective_id"] == "obj:a:1"

    def test_ordered_by_tier_index(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective(objective_id="obj:t2", slug="t2", tier_index=2))
        repo.save_objective(_objective(objective_id="obj:t0", slug="t0", tier_index=0))
        repo.save_objective(_objective(objective_id="obj:t1", slug="t1", tier_index=1))
        tiers = [o["tier_index"] for o in repo.get_objectives("campaign:test")]
        assert tiers == [0, 1, 2]

    def test_returns_empty_for_unknown_campaign(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective())
        assert repo.get_objectives("campaign:nope") == []


class TestUpsert:
    def test_upsert_no_duplicate_and_replaces_knowledge(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective(reveals_knowledge=["old secret"]))
        updated = _objective(reveals_knowledge=["new secret"]).model_copy(
            update={"title": "Restore the Reactor"}
        )
        repo.save_objective(updated)
        results = repo.get_objectives("campaign:test")
        assert len(results) == 1
        assert results[0]["title"] == "Restore the Reactor"
        assert results[0]["reveals_knowledge"] == ["new secret"]
