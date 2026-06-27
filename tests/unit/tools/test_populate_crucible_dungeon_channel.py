"""Tests for the Phase 51 dungeon-channel seed (`populate_crucible_dungeon_channel`).

Uses a real `MemoryRepository` on `tmp_path` (no mocks) and the real persona /
room-context / gate helpers, so the test proves the seed actually makes the
"Talk to the Dungeon" channel live end-to-end.
"""
from pathlib import Path

import pytest

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.dungeon_persona import (
    read_dungeon_knowledge,
    read_dungeon_voice,
)
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.dungeon_channel import dungeon_channel_available
from dungeon_daddy.rpg.models import ClockState
from dungeon_daddy.rpg.room_context import build_room_context
from tools.populate_crucible_dungeon_channel import (
    CAMPAIGN_ID,
    RESONANCE_ROOM_ID,
    seed_dungeon_channel,
)

_MIGRATIONS_DIR = Path("dungeon_daddy/data/migrations")


@pytest.fixture
def repo(tmp_path: Path):
    r = MemoryRepository(tmp_path / "campaign.duckdb")
    r.initialize_schema(_MIGRATIONS_DIR)
    r.save_campaign(
        campaign_id=CAMPAIGN_ID,
        slug="the-crucible",
        title="The Crucible",
        dungeon_slug="the-crucible",
    )
    yield r
    r.close()


def _intimacy_clock(repo: MemoryRepository) -> dict:
    return next(
        c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
    )


def test_seed_writes_persona_docs_and_campaign_refs(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    assert (tmp_path / "memory" / "dungeon" / "voice.md").exists()
    assert (tmp_path / "memory" / "dungeon" / "knowledge.md").exists()

    camp = repo.get_campaign(CAMPAIGN_ID)
    assert camp["dungeon_voice_path"] == "memory/dungeon/voice.md"
    assert camp["dungeon_knowledge_path"] == "memory/dungeon/knowledge.md"

    voice = read_dungeon_voice(tmp_path / camp["dungeon_voice_path"])
    assert voice and "forge" in voice.lower()
    secrets = read_dungeon_knowledge(tmp_path / camp["dungeon_knowledge_path"])
    assert len(secrets) >= 3


def test_seed_preserves_existing_campaign_fields(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    camp = repo.get_campaign(CAMPAIGN_ID)
    assert camp["slug"] == "the-crucible"
    assert camp["title"] == "The Crucible"
    assert camp["dungeon_slug"] == "the-crucible"


def test_seed_writes_recedable_intimacy_clock(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    clock = _intimacy_clock(repo)
    assert clock["monotonic"] is False
    assert clock["segments"] == 6
    assert clock["filled"] == 3
    assert clock["clock_level"] == "dungeon"


def test_seed_opens_channel_at_resonance_room(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    objs = repo.get_objects_by_room(CAMPAIGN_ID, RESONANCE_ROOM_ID)
    assert any(o["archetype"] == "resonance_point" for o in objs)

    ctx = build_room_context(
        RESONANCE_ROOM_ID,
        CAMPAIGN_ID,
        SessionState(dungeon_id="the-crucible"),
        repo,
    )
    assert ctx["resonance_point"] is True

    row = _intimacy_clock(repo)
    clock = ClockState(
        clock_id=row["clock_id"],
        campaign_id=row["campaign_id"],
        label=row["label"],
        segments=row["segments"],
        filled=row["filled"],
        status=row["status"],
        clock_level=row["clock_level"],
        category=row["category"],
        monotonic=row["monotonic"],
    )
    ok, reason = dungeon_channel_available(ctx, clock)
    assert ok is True
    assert reason is None


def test_seed_is_idempotent(repo, tmp_path: Path):
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    clocks = [
        c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
    ]
    assert len(clocks) == 1
    objs = [
        o
        for o in repo.get_objects_by_room(CAMPAIGN_ID, RESONANCE_ROOM_ID)
        if o["archetype"] == "resonance_point"
    ]
    assert len(objs) == 1


def test_seed_adopts_existing_intimacy_clock(repo, tmp_path: Path):
    # The canonical RPG seed authors a monotonic dungeon_intimacy clock; the
    # channel seed must adopt it (flip monotonic, open it) — not create a second.
    repo.save_clock(
        clock_id="clock:the-crucible:the-dungeon-learns-you",
        campaign_id=CAMPAIGN_ID,
        label="The Factory Learns What You Fear",
        segments=6,
        filled=2,
        category="dungeon_intimacy",
        clock_level="dungeon",
        monotonic=True,
    )

    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)

    clocks = [
        c for c in repo.get_clocks(CAMPAIGN_ID) if c["category"] == "dungeon_intimacy"
    ]
    assert len(clocks) == 1
    clock = clocks[0]
    assert clock["clock_id"] == "clock:the-crucible:the-dungeon-learns-you"
    assert clock["label"] == "The Factory Learns What You Fear"
    assert clock["monotonic"] is False
    assert clock["filled"] == 3  # raised from 2 to the cryptic threshold


def test_reseed_preserves_intimacy_progress(repo, tmp_path: Path):
    # Re-running the seed after play must not reset earned intimacy.
    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    clock = _intimacy_clock(repo)
    repo.update_clock_progress(clock["clock_id"], filled=5, status="active")

    seed_dungeon_channel(repo, tmp_path, CAMPAIGN_ID)
    assert _intimacy_clock(repo)["filled"] == 5
