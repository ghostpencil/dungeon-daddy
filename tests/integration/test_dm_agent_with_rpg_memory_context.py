"""Integration: DungeonMasterAgent.build_prompt() uses a real ContextBundle from real DuckDB."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.llm.provider import LLMMessage
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


class _MockProvider:
    def __init__(self, response: str = "The dungeon whispers.") -> None:
        self._response = response
        self.last_system = ""

    def complete(self, messages, system: str = "", max_tokens: int = 512) -> str:
        self.last_system = system
        return self._response

    @property
    def model_id(self) -> str:
        return "mock"


@pytest.fixture
def repo(tmp_path: Path):
    db = MemoryRepository(tmp_path / "campaign.duckdb")
    db.initialize_schema(MIGRATIONS_DIR)
    _seed(db)
    yield db
    db.close()


def _seed(repo: MemoryRepository) -> None:
    repo.save_campaign("camp-1", "slug-1", "Test Campaign")
    repo._conn.execute(
        "INSERT INTO scenes (scene_id, campaign_id, location_slug, status) VALUES (?, ?, ?, ?)",
        ["scene-1", "camp-1", "shadow-vault", "active"],
    )
    repo.save_memory_entry(
        "mem-1", "camp-1", "event", "The Vault Door",
        summary="Party found the vault door sealed.", importance=7,
    )


@pytest.fixture
def real_bundle(repo):
    return ContextBundleBuilder("camp-1", "scene-1", "run_scene", [], 1000).build(repo)


def _room():
    from dungeon_daddy.data.models import Room
    return Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")


def _level():
    from dungeon_daddy.data.models import Level, Room
    return Level(
        id=1, name="Vestibule", summary="Dark.", ecology="undead",
        loop="lock_key", width=10, height=10, entries=[],
        rooms=[Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")],
        connections=[],
    )


def _dungeon():
    from dungeon_daddy.data.models import Dungeon, DungeonMeta
    return Dungeon(
        meta=DungeonMeta(
            title="Shadow Keep", theme="Dark", setting="A keep.",
            party="2 heroes", quest="Escape.",
        ),
        levels=[_level()],
    )


# ---------------------------------------------------------------------------
# Bullet 4: DMAgent with real bundle builds prompt containing scene brief text
# ---------------------------------------------------------------------------

def test_build_prompt_with_real_bundle_contains_scene_location(real_bundle):
    agent = DungeonMasterAgent(provider=_MockProvider())
    prompt = agent.build_prompt(context_bundle=real_bundle)
    assert "shadow-vault" in prompt


def test_build_prompt_with_real_bundle_contains_memory_card_title(real_bundle):
    agent = DungeonMasterAgent(provider=_MockProvider())
    prompt = agent.build_prompt(context_bundle=real_bundle)
    assert "The Vault Door" in prompt


# ---------------------------------------------------------------------------
# Bullet 5: fallback (no bundle) still returns valid prompt — no regression
# ---------------------------------------------------------------------------

def test_build_prompt_fallback_no_bundle_returns_system_prompt():
    agent = DungeonMasterAgent(provider=_MockProvider())
    result = agent.build_prompt(context_bundle=None)
    assert result == agent._system_prompt


def test_respond_with_real_bundle_system_contains_scene_location(repo):
    bundle = ContextBundleBuilder("camp-1", "scene-1", "run_scene", [], 1000).build(repo)
    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[LLMMessage(role="user", content="Look around.")],
        room=_room(), level=_level(), dungeon=_dungeon(),
        context_bundle=bundle,
    )
    assert "shadow-vault" in provider.last_system


def test_respond_without_bundle_returns_provider_output():
    provider = _MockProvider(response="The dungeon whispers.")
    agent = DungeonMasterAgent(provider=provider)
    result = agent.respond(
        history=[LLMMessage(role="user", content="Look around.")],
        room=_room(), level=_level(), dungeon=_dungeon(),
    )
    assert result == "The dungeon whispers."
