"""Integration tests — Play Mode RPG wiring.

No mocks for RPG or memory layers. All repository interactions use real DuckDB
on tmp_path. Arcade and LLM calls remain mocked where required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActionRequest
from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.ui.panels.debug_controls import DebugControls

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)

CAMPAIGN_ID = "test_camp"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


@pytest.fixture
def rpg() -> RpgService:
    return RpgService()


# ---------------------------------------------------------------------------
# Test 1 — resolve action persists to repository
# ---------------------------------------------------------------------------

def test_resolve_action_persists_to_repository(rpg: RpgService, repo: MemoryRepository) -> None:
    debug = DebugControls(rpg_service=rpg, mem_repo=repo)
    req = ActionRequest(
        campaign_id=CAMPAIGN_ID,
        actor_id="pc_1",
        action_key="hunt",
        dice_pool=2,
    )
    resolution = debug.resolve_sample_action(req, fixed=[6, 3])

    rows = repo.get_action_resolutions(CAMPAIGN_ID)
    assert len(rows) == 1
    assert rows[0]["resolution_id"] == resolution.resolution_id
    assert rows[0]["outcome"] == resolution.outcome
    assert rows[0]["action_key"] == "hunt"


# ---------------------------------------------------------------------------
# Test 2 — apply stress persists to repository
# ---------------------------------------------------------------------------

def test_apply_stress_persists_to_repository(rpg: RpgService, repo: MemoryRepository) -> None:
    debug = DebugControls(rpg_service=rpg, mem_repo=repo)
    actor = rpg.create_actor(
        campaign_id=CAMPAIGN_ID, actor_type="pc",
        slug="brogan", display_name="Brogan",
    )
    body_track = actor.stress["body"]
    updated = debug.apply_stress(actor.actor_id, CAMPAIGN_ID, body_track, amount=2)

    rows = repo.get_actor_stress_tracks(actor.actor_id)
    assert len(rows) == 1
    assert rows[0]["track_key"] == "body"
    assert rows[0]["filled"] == updated.filled
    assert updated.filled == 2


# ---------------------------------------------------------------------------
# Test 3 — advance clock persists to repository
# ---------------------------------------------------------------------------

def test_advance_clock_persists_to_repository(rpg: RpgService, repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.clocks import create_clock

    debug = DebugControls(rpg_service=rpg, mem_repo=repo)
    clock = create_clock(campaign_id=CAMPAIGN_ID, label="Find the Key", segments=4)
    updated = debug.advance_clock(clock, ticks=2)

    rows = repo.get_clocks(CAMPAIGN_ID)
    assert len(rows) == 1
    assert rows[0]["clock_id"] == updated.clock_id
    assert rows[0]["filled"] == 2
    assert rows[0]["label"] == "Find the Key"


# ---------------------------------------------------------------------------
# Test 4 — memory inspector search from repository entries
# ---------------------------------------------------------------------------

def test_memory_inspector_search_returns_entries_from_repository(
    repo: MemoryRepository,
) -> None:
    from dungeon_daddy.memory.models import MemoryEntry
    from dungeon_daddy.ui.panels.memory_inspector_panel import MemoryInspectorPanel

    repo.save_memory_entry("m1", CAMPAIGN_ID, "note", "Elven Shrine", importance=7)
    repo.add_memory_tag("m1", "elf")
    repo.save_memory_entry("m2", CAMPAIGN_ID, "note", "Goblin Cache", importance=5)
    repo.add_memory_tag("m2", "goblin")

    raw = repo.get_memory_entries_by_campaign(CAMPAIGN_ID)
    entries = [
        MemoryEntry(
            memory_id=r["memory_id"],
            campaign_id=r["campaign_id"],
            type=r["type"],
            title=r["title"],
            summary=r["summary"] or "",
            status=r["status"],
            importance=r["importance"],
            markdown_path=r["markdown_path"],
            tags=repo.get_memory_tags(r["memory_id"]),
        )
        for r in raw
    ]

    panel = MemoryInspectorPanel()
    panel.set_entries(entries)

    panel.set_search_query("elf")
    results = panel.get_results()
    assert len(results) == 1
    assert results[0].title == "Elven Shrine"

    panel.set_search_query("")
    assert len(panel.get_results()) == 2


# ---------------------------------------------------------------------------
# Test 5 — sync report reflects repository state
# ---------------------------------------------------------------------------

def test_sync_report_reflects_repository_state(
    tmp_path: Path, repo: MemoryRepository
) -> None:
    from dungeon_daddy.memory.sync import SyncReporter

    memory_root = tmp_path / "rpg-memory"
    memory_root.mkdir()

    repo.save_memory_entry("m_no_path", CAMPAIGN_ID, "note", "Orphaned Entry")

    reporter = SyncReporter(repo=repo, memory_root=memory_root)
    issues = reporter.check()

    kinds = {issue.kind for issue in issues}
    assert "no_markdown_path" in kinds
    assert any(i.memory_id == "m_no_path" for i in issues)
