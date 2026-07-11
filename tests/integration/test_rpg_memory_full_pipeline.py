"""Phase 32 step 32-6 — RPG + memory full pipeline integration test.

End-to-end path: action roll → stress applied → fallout triggered →
memory entry created → context bundle built → DM prompt generated.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.models import ContextBundle
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.fallout import evaluate_fallout
from dungeon_daddy.rpg.models import (
    ActionRequest,
    ActionResolution,
    ActorState,
    FalloutRecord,
    StressTrack,
)
from dungeon_daddy.rpg.service import RpgService
from tests.fixtures.phase32_campaign import (
    CAMPAIGN_ID,
    MEM_SABLE_PACT_ID,
    SABLE_ID,
    SCENE_COMBAT_ID,
    seed_campaign,
)

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent / "dungeon_daddy" / "data" / "migrations"
)


@dataclass
class _PipelineResult:
    repo: MemoryRepository
    resolution: ActionResolution
    body_after_action: StressTrack
    new_fallout: FalloutRecord
    new_memory_id: str
    bundle: ContextBundle
    prompt: str


def _run_pipeline(tmp_path: Path) -> _PipelineResult:
    db = MemoryRepository(tmp_path / "campaign.duckdb")
    db.initialize_schema(MIGRATIONS_DIR)
    seed_campaign(db)

    svc = RpgService()

    # Bullet 1 — action roll with push_yourself → stress_cost = 1
    request = ActionRequest(
        campaign_id=CAMPAIGN_ID,
        actor_id=SABLE_ID,
        action_key="skirmish",
        scene_id=SCENE_COMBAT_ID,
        dice_pool=2,
        push_yourself=True,
    )
    # fixed=[1,1,1]: pool = dice_pool(2) + push_die(1) = 3 dice, all miss
    resolution, _ = svc.resolve_action(request, fixed=[1, 1, 1])

    # Bullet 2 — apply stress_cost to body track (3 → 4)
    body = StressTrack(track_key="body", capacity=6, filled=3)
    body_after_action, _ = svc.apply_stress(
        SABLE_ID, CAMPAIGN_ID, body, amount=resolution.stress_cost
    )
    db.save_actor_stress_track(
        SABLE_ID, "body", body_after_action.capacity, body_after_action.filled
    )

    # Fill track to capacity to trigger fallout (4 + 2 → 6)
    body_filled, _ = svc.apply_stress(SABLE_ID, CAMPAIGN_ID, body_after_action, amount=2)
    db.save_actor_stress_track(SABLE_ID, "body", body_filled.capacity, body_filled.filled)

    # Bullet 3 — trigger fallout; reset body track
    sable = ActorState(
        actor_id=SABLE_ID,
        campaign_id=CAMPAIGN_ID,
        actor_type="pc",
        slug="sable",
        display_name="Sable",
        stress={"body": body_filled},
    )
    new_fallout, reset_body = evaluate_fallout(
        sable, "body", CAMPAIGN_ID, existing_fallout=None
    )
    db.save_fallout_record(new_fallout)
    db.save_actor_stress_track(SABLE_ID, "body", reset_body.capacity, reset_body.filled)

    # Bullet 4 — memory entry referencing the fallout event
    new_memory_id = f"mem-pipeline-{uuid.uuid4()}"
    db.save_memory_entry(
        new_memory_id,
        CAMPAIGN_ID,
        "event",
        f"Fallout: {new_fallout.title}",
        summary=(
            f"Sable suffered {new_fallout.title} after the forge-floor confrontation."
        ),
        status="approved",
        importance=7,
    )
    db.add_memory_tag(new_memory_id, "actor:pc:sable")

    # Bullet 5 — build context bundle
    bundle = ContextBundleBuilder(
        CAMPAIGN_ID, SCENE_COMBAT_ID, "run_scene", [SABLE_ID], 10_000
    ).build(db)

    # Bullet 6 — build DM prompt
    agent = DungeonMasterAgent(provider=MagicMock())
    prompt = agent.build_prompt(bundle)

    return _PipelineResult(
        repo=db,
        resolution=resolution,
        body_after_action=body_after_action,
        new_fallout=new_fallout,
        new_memory_id=new_memory_id,
        bundle=bundle,
        prompt=prompt,
    )


@pytest.fixture
def pipeline(tmp_path: Path):
    result = _run_pipeline(tmp_path)
    yield result
    result.repo.close()


# ---------------------------------------------------------------------------
# Bullet 1: action roll with push_yourself applies stress_cost = 1
# ---------------------------------------------------------------------------


class TestActionRoll:
    def test_push_yourself_yields_stress_cost_of_one(self, pipeline):
        assert pipeline.resolution.stress_cost == 1

    def test_action_roll_outcome_is_valid(self, pipeline):
        assert pipeline.resolution.outcome in {"critical", "full", "partial", "miss"}


# ---------------------------------------------------------------------------
# Bullet 2: stress track incremented after applying stress_cost
# ---------------------------------------------------------------------------


class TestStressIncrement:
    def test_body_track_incremented_by_stress_cost(self, pipeline):
        # golden fixture body.filled=3; push_yourself adds 1 → 4
        assert pipeline.body_after_action.filled == 4

    def test_body_track_in_repo_reflects_increment(self, pipeline):
        tracks = pipeline.repo.get_actor_stress_tracks(SABLE_ID)
        body = next(t for t in tracks if t["track_key"] == "body")
        # after fallout the track resets to 0
        assert body["filled"] == 0


# ---------------------------------------------------------------------------
# Bullet 3: fallout record created and persisted
# ---------------------------------------------------------------------------


class TestFalloutCreated:
    def test_fallout_record_in_repo(self, pipeline):
        records = pipeline.repo.get_fallout_records(CAMPAIGN_ID, SABLE_ID)
        ids = {r["fallout_id"] for r in records}
        assert pipeline.new_fallout.fallout_id in ids

    def test_new_fallout_is_minor_body(self, pipeline):
        assert pipeline.new_fallout.track_key == "body"
        assert pipeline.new_fallout.severity == "minor"
        assert pipeline.new_fallout.title == "Battered"


# ---------------------------------------------------------------------------
# Bullet 4 + 5: new memory entry appears in context bundle
# ---------------------------------------------------------------------------


class TestMemoryInBundle:
    def test_new_memory_card_present_in_bundle(self, pipeline):
        ids = {c["memory_id"] for c in pipeline.bundle.memory_cards}
        assert pipeline.new_memory_id in ids

    def test_bundle_holds_the_scene_scoped_memories(self, pipeline):
        # Slice A5: retrieval is scene-scoped to the focus PC (Sable, no room),
        # so only Sable-tagged memories land — the golden pact + the new fallout
        # memory (both actor:pc:sable), not the golem/informant/location lore.
        ids = {c["memory_id"] for c in pipeline.bundle.memory_cards}
        assert pipeline.new_memory_id in ids
        assert MEM_SABLE_PACT_ID in ids
        assert len(ids) == 2


# ---------------------------------------------------------------------------
# Bullet 6: DM prompt contains fallout title
# ---------------------------------------------------------------------------


class TestDMPrompt:
    def test_fallout_title_in_prompt(self, pipeline):
        assert pipeline.new_fallout.title in pipeline.prompt

    def test_prompt_contains_fallout_section(self, pipeline):
        assert "Active Fallout" in pipeline.prompt
