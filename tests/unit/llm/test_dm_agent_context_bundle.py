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
    assert "(importance: 8)" in result


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
    from dungeon_daddy.data.models import Level, Room
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
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent as DMA
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

# ---------------------------------------------------------------------------
# Slice A6 (T7): the deterministic pre-fetch renders as a distinct
# `# Related Lore` section so the DM actually sees it.
# ---------------------------------------------------------------------------

def test_build_prompt_renders_related_lore_section():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(related_lore=[
        {"memory_id": "L-1", "title": "The Old Pact", "summary": "A bargain struck in blood.", "importance": 5},
    ])
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Related Lore" in result
    assert "The Old Pact" in result
    assert "A bargain struck in blood." in result


def test_build_prompt_omits_related_lore_section_when_empty():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(related_lore=[])
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Related Lore" not in result


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


# ---------------------------------------------------------------------------
# Slice B4 review fix (L7): the bundle sections the prompt used to drop.
#
# `bundle_entity_ids` (llm/lookup_tool.py) treats the whole ContextBundle as
# "the narrator's context" and drives the full-overlap redirect. Present actors,
# loose items and factions were collected there but never rendered here — so a
# lookup for an NPC standing in the room came back "already in your context"
# with no data behind it. The guard test at the bottom of this file pins the
# coupling; these pin the rendering.
# ---------------------------------------------------------------------------

def _room_with(**kwargs):
    room = {
        "room_id": "1-A",
        "objects": [], "loose_items": [], "npcs": [], "monsters": [], "exits": [],
    }
    room.update(kwargs)
    return room


def test_build_prompt_includes_present_npcs():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(current_room=_room_with(npcs=[{
        "actor_id": "npc-1", "slug": "pinion", "display_name": "Pinion, the Caretaker Cog",
        "status": "alive", "disposition": "friendly",
    }]))
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Present Actors" in result
    assert "Pinion, the Caretaker Cog" in result
    assert "friendly" in result


def test_build_prompt_includes_present_monsters():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(current_room=_room_with(monsters=[{
        "actor_id": "mon-1", "slug": "scorpion-swarm", "display_name": "Scorpion Swarm",
        "status": "alive", "disposition": "hostile",
    }]))
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Present Actors" in result
    assert "Scorpion Swarm" in result
    assert "hostile" in result


def test_build_prompt_omits_present_actors_section_when_room_is_empty():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(current_room=_room_with())
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Present Actors" not in result


def test_build_prompt_includes_loose_items():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(current_room=_room_with(loose_items=[{
        "item_id": "item-1", "slug": "travel-journal",
        "display_name": "Sun-Bleached Travel Journal",
        "description": "Salt-stiffened pages, a merchant's hand.", "status": "present",
    }]))
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Loose Items" in result
    assert "Sun-Bleached Travel Journal" in result
    assert "Salt-stiffened pages, a merchant's hand." in result


def test_build_prompt_includes_factions():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(faction_reputations=[{
        "faction_id": "fac-1", "slug": "forge-wardens", "display_name": "Forge Wardens",
        "reputation": 2, "goal": "Reclaim the forge", "tier": 1, "status": "active",
    }])
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Factions" in result
    assert "Forge Wardens" in result
    assert "Reclaim the forge" in result


def test_build_prompt_omits_factions_section_when_empty():
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(faction_reputations=[])
    result = agent.build_prompt(context_bundle=bundle)
    assert "# Factions" not in result


def test_build_prompt_includes_clock_stakes():
    # `stakes` is the clock's snippet in search_entities, so a redirected clock
    # lookup claims the narrator already has it.
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    agent = DungeonMasterAgent(provider=_MockProvider())
    bundle = _make_bundle(open_clocks=[{
        "clock_id": "clk-1", "label": "Ritual Countdown", "segments": 6, "filled": 3,
        "status": "active", "stakes": "The wards fail and the vault floods.",
    }])
    result = agent.build_prompt(context_bundle=bundle)
    assert "Ritual Countdown" in result
    assert "The wards fail and the vault floods." in result


# ---------------------------------------------------------------------------
# The L7 coupling guard (Slice B4 review fix).
# ---------------------------------------------------------------------------

def test_every_bundle_entity_id_is_described_in_the_system_prompt():
    """Everything `bundle_entity_ids` collects must be readable in the prompt.

    That set drives the L7 full-overlap redirect — the narrator is told
    "Already in your context — do not look this up again". If an id reaches the
    set without its entity reaching the prompt, the redirect withholds data the
    model never had, and there is no second tool round to recover in.
    """
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.llm.lookup_tool import bundle_entity_ids
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider()
    agent = DungeonMasterAgent(provider=provider)
    bundle = _make_bundle(
        memory_cards=[{
            "memory_id": "m-1", "title": "Pact with the Shadow",
            "summary": "Party agreed to spare the wraith.", "importance": 8,
        }],
        related_lore=[{
            "memory_id": "L-1", "title": "The Old Pact",
            "summary": "A bargain struck in blood.", "importance": 5,
        }],
        open_clocks=[{
            "clock_id": "clk-1", "label": "Ritual Countdown", "segments": 6,
            "filled": 3, "status": "active", "stakes": "The wards fail.",
        }],
        faction_reputations=[{
            "faction_id": "fac-1", "slug": "forge-wardens",
            "display_name": "Forge Wardens", "reputation": 2,
            "goal": "Reclaim the forge", "tier": 1, "status": "active",
        }],
        current_room=_room_with(
            objects=[{
                "object_id": "obj-1", "slug": "notice-board",
                "display_name": "Warden's Notice Board", "archetype": "lore_fixture",
                "current_state": "default", "description": "A bounty notice.",
            }],
            loose_items=[{
                "item_id": "item-1", "slug": "travel-journal",
                "display_name": "Sun-Bleached Travel Journal",
                "description": "Salt-stiffened pages.", "status": "present",
            }],
            npcs=[{
                "actor_id": "npc-1", "slug": "pinion", "display_name": "Pinion",
                "status": "alive", "disposition": "friendly",
            }],
            monsters=[{
                "actor_id": "mon-1", "slug": "scorpion-swarm",
                "display_name": "Scorpion Swarm", "status": "alive",
                "disposition": "hostile",
            }],
        ),
    )
    # `respond` is the real seam: the room itself is described by _build_context
    # from the dungeon JSON, not by build_prompt, so only the assembled system
    # prompt shows the narrator's whole context.
    agent.respond(
        history=[LLMMessage(role="user", content="Look around.")],
        room=_make_room(), level=_make_level(), dungeon=_make_dungeon(),
        context_bundle=bundle,
    )
    system = provider.last_system

    # id -> the text that proves the narrator can actually read that entity.
    described = {
        "m-1": "Pact with the Shadow",
        "L-1": "The Old Pact",
        "clk-1": "Ritual Countdown",
        "fac-1": "Forge Wardens",
        "1-A": "Entry Hall",  # the current room, via _build_context
        "obj-1": "Warden's Notice Board",
        "item-1": "Sun-Bleached Travel Journal",
        "npc-1": "Pinion",
        "mon-1": "Scorpion Swarm",
    }
    assert bundle_entity_ids(bundle) == set(described), (
        "bundle_entity_ids changed: a category joined or left the L7 overlap "
        "set. Anything it collects must also be rendered into the prompt."
    )
    for entity_id, proof in described.items():
        assert proof in system, (
            f"{entity_id} drives an L7 redirect but {proof!r} is not in the "
            "system prompt — the narrator would be refused data it never had."
        )
