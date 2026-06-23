"""Tests for DungeonMasterAgent.build_prompt() with ContextBundle integration."""
from __future__ import annotations


class _MockProvider:
    def __init__(self, response="The shadows shift."):
        self._response = response
        self.last_system = ""
        self.last_messages = []

    def complete(self, messages, system="", max_tokens=512):
        self.last_system = system
        self.last_messages = messages
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_bundle(**kwargs):
    from dungeon_daddy.memory.models import ContextBundle
    defaults = dict(
        bundle_id="b-001",
        campaign_id="camp-1",
        scene_id="scene-1",
        mode="run_scene",
        scene_brief={"scene_id": "scene-1", "location_slug": "crypt-entrance", "status": "active"},
        mechanical_state={"actor-1": {"action_ratings": {"skirmish": 2}, "stress_tracks": {"body": 3}}},
        active_fallout=[{"actor_id": "actor-1", "title": "Broken arm", "status": "active"}],
        open_clocks=[{"clock_id": "clk-1", "name": "Ritual Countdown", "segments": 6, "filled": 3, "status": "active"}],
        memory_cards=[
            {"memory_id": "m-1", "title": "Pact with the Shadow", "summary": "Party agreed to spare the wraith.", "importance": 8},
        ],
        must_remember=[],
        provenance={"retrieved": 1, "omitted": 0, "focus_actor_ids": ["actor-1"]},
    )
    defaults.update(kwargs)
    return ContextBundle(**defaults)


# ---------------------------------------------------------------------------
# Bullet 1: build_prompt(context_bundle=None) returns base system prompt
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bullet 2: scene_brief included when bundle provided
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bullet 3: memory cards as numbered list with title, summary, importance
# ---------------------------------------------------------------------------

def test_build_prompt_with_bundle_includes_memory_card_title():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(memory_cards=[
        {"memory_id": "m-1", "title": "Pact with the Shadow", "summary": "Party agreed to spare the wraith.", "importance": 8},
        {"memory_id": "m-2", "title": "Lost Amulet", "summary": "Dropped near the altar.", "importance": 6},
    ])
    result = agent.build_prompt(context_bundle=bundle)
    assert "1." in result
    assert "2." in result
    assert "Pact with the Shadow" in result
    assert "Lost Amulet" in result
    assert "importance" in result.lower() or "8" in result


def test_build_prompt_with_bundle_includes_memory_card_summary():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle()
    result = agent.build_prompt(context_bundle=bundle)
    assert "Party agreed to spare the wraith." in result


# ---------------------------------------------------------------------------
# Bullet 4: active fallout and open clocks in Mechanical Context block
# ---------------------------------------------------------------------------

def test_build_prompt_with_bundle_includes_fallout():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle()
    result = agent.build_prompt(context_bundle=bundle)
    assert "Broken arm" in result
    assert "Mechanical Context" in result


def test_build_prompt_with_bundle_includes_open_clocks():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle()
    result = agent.build_prompt(context_bundle=bundle)
    assert "Ritual Countdown" in result


# ---------------------------------------------------------------------------
# Bullet 5: respond() accepts context_bundle and uses build_prompt output
# ---------------------------------------------------------------------------

def _make_room():
    from dungeon_daddy.data.models import Room
    return Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")

def _make_level():
    from dungeon_daddy.data.models import Connection, Level, Room
    return Level(
        id=1, name="Vestibule", summary="Flooded.", ecology="goblins",
        loop="lock_key", width=10, height=10, entries=[],
        rooms=[Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")],
        connections=[],
    )

def _make_dungeon():
    from dungeon_daddy.data.models import Dungeon, DungeonMeta
    return Dungeon(
        meta=DungeonMeta(title="Test Tomb", theme="Undead", setting="A tomb.", party="4 heroes", quest="Find the crown."),
        levels=[_make_level()],
    )


def test_respond_with_bundle_system_contains_scene_brief():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.provider import LLMMessage
    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    bundle = _make_bundle()
    agent.respond(
        history=[LLMMessage(role="user", content="Look around.")],
        room=_make_room(), level=_make_level(), dungeon=_make_dungeon(),
        context_bundle=bundle,
    )
    assert "crypt-entrance" in provider.last_system


def test_respond_without_bundle_no_regression():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent, DungeonMasterAgent as DMA
    from dungeon_daddy.llm.provider import LLMMessage
    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    agent.respond(
        history=[LLMMessage(role="user", content="Look around.")],
        room=_make_room(), level=_make_level(), dungeon=_make_dungeon(),
    )
    assert provider.last_system.startswith(DMA.SYSTEM_PROMPT)


def test_respond_with_bundle_returns_provider_output():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.provider import LLMMessage
    provider = _MockProvider(response="You see darkness.")
    agent = DungeonMasterAgent(provider=provider)
    result = agent.respond(
        history=[LLMMessage(role="user", content="Look.")],
        room=_make_room(), level=_make_level(), dungeon=_make_dungeon(),
        context_bundle=_make_bundle(),
    )
    assert result == "You see darkness."


# ---------------------------------------------------------------------------
# Bullet 6: draft memory cards are labelled [DRAFT]
# ---------------------------------------------------------------------------

def test_build_prompt_draft_card_labelled():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(memory_cards=[
        {"memory_id": "m-1", "title": "Rumour of Betrayal", "summary": "Unverified intel.", "importance": 5, "draft": True},
    ])
    result = agent.build_prompt(context_bundle=bundle)
    assert "[DRAFT]" in result
    assert "Rumour of Betrayal" in result


def test_build_prompt_non_draft_card_not_labelled():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle()
    result = agent.build_prompt(context_bundle=bundle)
    assert "[DRAFT]" not in result


def test_build_prompt_with_bundle_includes_scene_location():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle()
    result = agent.build_prompt(context_bundle=bundle)
    assert "crypt-entrance" in result
    assert "active" in result


def test_build_prompt_no_bundle_returns_system_prompt():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    result = agent.build_prompt(context_bundle=None)
    assert result == DungeonMasterAgent.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Room contents: the current_room block's objects (name + description) are
# rendered so the DM can narrate what the party studies/interacts with.
# ---------------------------------------------------------------------------

def test_build_prompt_includes_room_object_description():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(current_room={
        "room_id": "r1",
        "objects": [{
            "object_id": "obj-board", "slug": "notice-board",
            "display_name": "Warden's Notice Board", "archetype": "lore_fixture",
            "current_state": "default",
            "description": "A bounty for the missing lift-warden's key.",
        }],
        "loose_items": [], "npcs": [], "monsters": [], "exits": [],
    })
    result = agent.build_prompt(context_bundle=bundle)
    assert "Warden's Notice Board" in result
    assert "A bounty for the missing lift-warden's key." in result
