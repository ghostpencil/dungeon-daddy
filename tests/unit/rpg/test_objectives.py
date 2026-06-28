"""Phase 51.5 Slices 3–4 — completion predicate + objective service (spec §4.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import Objective, ObjectiveCompletion, RoomObject
from dungeon_daddy.rpg.objectives import advance_objectives, completion_satisfied

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


class TestCompletionSatisfiedObjectState:
    def test_target_object_at_required_state_is_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )
        world_state = {"objects": [{"slug": "coolant-loop", "current_state": "restored"}]}

        assert completion_satisfied(completion, world_state) is True

    def test_target_object_in_wrong_state_is_not_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )
        world_state = {"objects": [{"slug": "coolant-loop", "current_state": "damaged"}]}

        assert completion_satisfied(completion, world_state) is False

    def test_target_object_absent_is_not_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )
        world_state = {"objects": [{"slug": "reactor", "current_state": "restored"}]}

        assert completion_satisfied(completion, world_state) is False

    def test_empty_world_state_is_not_satisfied(self) -> None:
        completion = ObjectiveCompletion(
            kind="object_state", target_slug="coolant-loop", required_state="restored"
        )

        assert completion_satisfied(completion, {}) is False


class TestCompletionSatisfiedUnsupportedKind:
    def test_unsupported_kind_raises(self) -> None:
        completion = ObjectiveCompletion(kind="item_obtained", target_slug="cipher-key")

        with pytest.raises(NotImplementedError):
            completion_satisfied(completion, {"objects": []})


# ---------------------------------------------------------------------------
# Slice 4 — advance_objectives service (spec §4.3.2, D4/D5/D6)
# ---------------------------------------------------------------------------

CAMPAIGN = "campaign:test"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _objective(
    objective_id: str = "obj:tier0",
    slug: str = "restore-coolant-loop",
    tier_index: int = 0,
    status: str = "active",
    target_slug: str = "coolant-valve",
    required_state: str = "restored",
    advances_clock_slug: str | None = "dungeon_intimacy",
    reveals_knowledge: list[str] | None = None,
) -> Objective:
    return Objective(
        objective_id=objective_id,
        campaign_id=CAMPAIGN,
        slug=slug,
        title="Restore the Coolant Loop",
        description="The dungeon wants its coolant loop restored.",
        tier_index=tier_index,
        status=status,
        completion=ObjectiveCompletion(
            kind="object_state",
            target_slug=target_slug,
            required_state=required_state,
        ),
        advances_clock_slug=advances_clock_slug,
        reveals_knowledge=reveals_knowledge or [],
    )


def _subsystem(
    slug: str = "coolant-valve",
    current_state: str = "restored",
    object_id: str | None = None,
) -> RoomObject:
    return RoomObject(
        object_id=object_id or f"obj:{slug}",
        campaign_id=CAMPAIGN,
        room_id="r01",
        level_id="L1",
        slug=slug,
        display_name="Coolant Valve",
        archetype="mechanism",
        description="A restorable subsystem.",
        current_state=current_state,
    )


def _intimacy_clock(repo: MemoryRepository, segments: int = 3, filled: int = 0) -> None:
    repo.save_clock(
        clock_id="clk:intimacy",
        campaign_id=CAMPAIGN,
        label="The dungeon learns you",
        segments=segments,
        filled=filled,
        category="dungeon_intimacy",
        monotonic=True,
    )


class TestAdvanceObjectives:
    def test_satisfied_active_objective_is_marked_completed(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_objective(_objective())
        repo.save_room_object(_subsystem(current_state="restored"))

        results = advance_objectives(repo, CAMPAIGN)

        assert [r.objective_id for r in results] == ["obj:tier0"]
        assert repo.get_objectives(CAMPAIGN)[0]["status"] == "completed"

    def test_ticks_and_persists_intimacy_clock(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective())
        repo.save_room_object(_subsystem(current_state="restored"))
        _intimacy_clock(repo, segments=3, filled=0)

        results = advance_objectives(repo, CAMPAIGN)

        assert results[0].clock is not None
        assert results[0].clock.filled == 1
        persisted = repo.get_clocks(CAMPAIGN)[0]
        assert persisted["filled"] == 1

    def test_completing_a_tier_activates_the_next_tier(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_objective(_objective(objective_id="obj:tier0", tier_index=0, status="active"))
        repo.save_objective(
            _objective(
                objective_id="obj:tier1",
                slug="restore-reactor",
                tier_index=1,
                status="locked",
                target_slug="reactor-core",
            )
        )
        repo.save_room_object(_subsystem(slug="coolant-valve", current_state="restored"))

        results = advance_objectives(repo, CAMPAIGN)

        assert results[0].activated_objective_ids == ["obj:tier1"]
        by_id = {o["objective_id"]: o for o in repo.get_objectives(CAMPAIGN)}
        assert by_id["obj:tier1"]["status"] == "active"

    def test_drafts_a_dungeon_state_memory(self, repo: MemoryRepository) -> None:
        repo.save_objective(_objective())
        repo.save_room_object(_subsystem(current_state="restored"))

        results = advance_objectives(repo, CAMPAIGN)

        entry = repo.get_memory_entry(results[0].memory_id)
        assert entry is not None
        assert entry["type"] == "dungeon_state"
        assert entry["status"] == "draft"

    def test_unsatisfied_objective_is_left_untouched(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_objective(_objective())
        repo.save_room_object(_subsystem(current_state="damaged"))  # not yet restored
        _intimacy_clock(repo, segments=3, filled=0)

        results = advance_objectives(repo, CAMPAIGN)

        assert results == []
        assert repo.get_objectives(CAMPAIGN)[0]["status"] == "active"
        assert repo.get_clocks(CAMPAIGN)[0]["filled"] == 0
        assert repo.get_memory_entries_by_campaign(CAMPAIGN) == []

    def test_only_active_objectives_are_evaluated(
        self, repo: MemoryRepository
    ) -> None:
        # A locked tier-0 objective whose subsystem is already restored must NOT
        # complete — progression is gated on the objective being active first.
        repo.save_objective(_objective(status="locked"))
        repo.save_room_object(_subsystem(current_state="restored"))

        assert advance_objectives(repo, CAMPAIGN) == []
        assert repo.get_objectives(CAMPAIGN)[0]["status"] == "locked"

    def test_completes_without_a_clock(self, repo: MemoryRepository) -> None:
        # No advances_clock_slug and no intimacy clock seeded: the objective
        # still completes and drafts memory; the result carries no clock.
        repo.save_objective(_objective(advances_clock_slug=None))
        repo.save_room_object(_subsystem(current_state="restored"))

        results = advance_objectives(repo, CAMPAIGN)

        assert results[0].clock is None
        assert repo.get_objectives(CAMPAIGN)[0]["status"] == "completed"
