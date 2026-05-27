"""Tests for DungeonBrief, LevelBrief, and DungeonWizardAgent."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, response=""):
        self._response = response
        self.last_system = ""
        self.last_messages = []

    def complete(self, messages, system="", max_tokens=1024):
        self.last_system = system
        self.last_messages = messages
        return self._response

    @property
    def model_id(self):
        return "mock"


def _make_loop_patterns():
    from dungeon_daddy.data.models import LoopPattern
    return {
        "lock_key": LoopPattern(
            key="lock_key", name="Lock & Key", blurb="Classic gating.",
            path_a_length="short", path_b_length="long",
            beats=["entry", "locked door", "key", "goal"],
            source="test",
        ),
        "gambit": LoopPattern(
            key="gambit", name="Gambit", blurb="Risk/reward.",
            path_a_length="medium", path_b_length="medium",
            beats=["entry", "choice", "goal"],
            source="test",
        ),
    }


BRIEF_RESPONSE = """
Here is your dungeon brief!

```brief
{
  "title": "Tomb of the Forgotten King",
  "theme": "Undead",
  "setting": "A collapsed royal tomb beneath a cursed moor.",
  "party": "4 adventurers, level 3, mixed",
  "quest": "Recover the Crown of Kings.",
  "num_levels": 3,
  "gm_notes": "Make it spooky. Add a trap in level 2."
}
```

Shall we begin generation?
"""

NO_BRIEF_RESPONSE = """
Great! Tell me a bit more about the party's composition.
How many players, and what classes are they playing?
"""


# ---------------------------------------------------------------------------
# Behavior 1: DungeonBrief is a dataclass with all required fields
# ---------------------------------------------------------------------------


def test_dungeon_brief_fields():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief
    brief = DungeonBrief(
        title="Test", theme="Horror", setting="A castle.",
        party="2 players", quest="Find the gem.",
        num_levels=2, gm_notes="",
    )
    assert brief.title == "Test"
    assert brief.num_levels == 2


# ---------------------------------------------------------------------------
# Behavior 2: DungeonWizardAgent.chat() calls provider.complete()
# ---------------------------------------------------------------------------

def test_wizard_chat_calls_provider(mocker):
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider(response="Tell me about your party.")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    history = [LLMMessage(role="user", content="Let's build a dungeon.")]
    result = agent.chat(history)
    assert result == "Tell me about your party."


def test_wizard_chat_passes_history_to_provider():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
    from dungeon_daddy.llm.provider import LLMMessage

    provider = _MockProvider(response="ok")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    history = [
        LLMMessage(role="user", content="msg1"),
        LLMMessage(role="assistant", content="msg2"),
    ]
    agent.chat(history)
    assert provider.last_messages == history


def test_wizard_chat_system_includes_system_prompt():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    agent.chat([])
    assert len(provider.last_system) > 0


def test_wizard_chat_system_includes_loop_patterns():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    agent.chat([], phase=2)
    # Both pattern names should appear in the phase-2 system prompt
    assert "Lock & Key" in provider.last_system
    assert "Gambit" in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 3: parse_brief() extracts DungeonBrief from a ```brief``` block
# ---------------------------------------------------------------------------

def test_parse_brief_returns_brief_when_block_present():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief, DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns={})
    brief = agent.parse_brief(BRIEF_RESPONSE)
    assert isinstance(brief, DungeonBrief)


def test_parse_brief_extracts_correct_fields():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns={})
    brief = agent.parse_brief(BRIEF_RESPONSE)
    assert brief.title == "Tomb of the Forgotten King"
    assert brief.theme == "Undead"
    assert brief.num_levels == 3
    assert "trap" in brief.gm_notes


# ---------------------------------------------------------------------------
# Behavior 4: parse_brief() returns None when no ```brief``` block is present
# ---------------------------------------------------------------------------

def test_parse_brief_returns_none_when_no_block():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns={})
    result = agent.parse_brief(NO_BRIEF_RESPONSE)
    assert result is None


def test_parse_brief_returns_none_on_empty_string():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns={})
    assert agent.parse_brief("") is None


# ---------------------------------------------------------------------------
# Behavior 5: _build_pattern_list() formats patterns for the system prompt
# ---------------------------------------------------------------------------

def test_build_pattern_list_includes_all_pattern_names():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    listing = agent._build_pattern_list()
    assert "Lock & Key" in listing
    assert "Gambit" in listing


def test_build_pattern_list_includes_blurbs():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    listing = agent._build_pattern_list()
    assert "Classic gating." in listing
    assert "Risk/reward." in listing


# ---------------------------------------------------------------------------
# Behavior 6: LevelBrief is a dataclass with required fields
# ---------------------------------------------------------------------------


def test_level_brief_required_fields():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    brief = LevelBrief(level_number=1, ecology="undead crypt", main_loop_pattern="lock_key")
    assert brief.level_number == 1
    assert brief.ecology == "undead crypt"
    assert brief.main_loop_pattern == "lock_key"
    assert brief.sub_loop_pattern is None


def test_level_brief_with_sub_loop():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    brief = LevelBrief(level_number=2, ecology="goblin warrens", main_loop_pattern="gambit", sub_loop_pattern="lock_key")
    assert brief.sub_loop_pattern == "lock_key"


def test_level_brief_gm_notes_defaults_to_empty():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lock_key")
    assert brief.gm_notes == ""


# ---------------------------------------------------------------------------
# Behavior 7: parse_level_brief() extracts LevelBrief from a ```level_brief``` block
# ---------------------------------------------------------------------------

LEVEL_BRIEF_RESPONSE = """
Sounds great! Here is the level brief.

```level_brief
{
  "level_number": 1,
  "ecology": "undead crypt",
  "main_loop_pattern": "lock_key"
}
```

Generating now...
"""

LEVEL_BRIEF_WITH_SUB_RESPONSE = """
```level_brief
{
  "level_number": 2,
  "ecology": "goblin warrens",
  "main_loop_pattern": "gambit",
  "sub_loop_pattern": "lock_key"
}
```
"""

LEVEL_BRIEF_NO_MAIN_RESPONSE = """
```level_brief
{
  "level_number": 1,
  "ecology": "forest shrine"
}
```
"""

LEVEL_BRIEF_WITH_NOTES_RESPONSE = """
```level_brief
{
  "level_number": 1,
  "ecology": "fungal cavern",
  "main_loop_pattern": "lock_key",
  "gm_notes": "Giant mushroom boss room, poison gas trap near the entrance"
}
```
"""


def test_parse_level_brief_returns_level_brief_when_block_present():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent, LevelBrief

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    result = agent.parse_level_brief(LEVEL_BRIEF_RESPONSE)
    assert isinstance(result, LevelBrief)


def test_parse_level_brief_extracts_correct_fields():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    result = agent.parse_level_brief(LEVEL_BRIEF_RESPONSE)
    assert result.level_number == 1
    assert result.ecology == "undead crypt"
    assert result.main_loop_pattern == "lock_key"


def test_parse_level_brief_extracts_sub_loop_when_present():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    result = agent.parse_level_brief(LEVEL_BRIEF_WITH_SUB_RESPONSE)
    assert result.sub_loop_pattern == "lock_key"


def test_parse_level_brief_sub_loop_is_none_when_absent():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    result = agent.parse_level_brief(LEVEL_BRIEF_RESPONSE)
    assert result.sub_loop_pattern is None


def test_parse_level_brief_returns_none_when_no_block():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    assert agent.parse_level_brief(NO_BRIEF_RESPONSE) is None


def test_parse_level_brief_returns_none_on_empty_string():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    assert agent.parse_level_brief("") is None


def test_parse_level_brief_returns_none_on_malformed_json():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    assert agent.parse_level_brief("```level_brief\nnot json\n```") is None


def test_parse_level_brief_extracts_gm_notes_when_present():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    result = agent.parse_level_brief(LEVEL_BRIEF_WITH_NOTES_RESPONSE)
    assert result.gm_notes == "Giant mushroom boss room, poison gas trap near the entrance"


def test_parse_level_brief_gm_notes_defaults_to_empty_when_absent():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=_make_loop_patterns())
    result = agent.parse_level_brief(LEVEL_BRIEF_RESPONSE)
    assert result.gm_notes == ""


def test_parse_level_brief_picks_random_main_loop_when_absent():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    patterns = _make_loop_patterns()
    agent = DungeonWizardAgent(provider=_MockProvider(), loop_patterns=patterns)
    result = agent.parse_level_brief(LEVEL_BRIEF_NO_MAIN_RESPONSE)
    assert result is not None
    assert result.main_loop_pattern in patterns


# ---------------------------------------------------------------------------
# Behavior 8: chat() routes to correct system prompt based on phase
# ---------------------------------------------------------------------------

def test_chat_phase1_excludes_loop_patterns():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    agent.chat([], phase=1)
    assert "Lock & Key" not in provider.last_system
    assert "Gambit" not in provider.last_system


def test_chat_phase2_includes_loop_patterns():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    agent.chat([], phase=2)
    assert "Lock & Key" in provider.last_system
    assert "Gambit" in provider.last_system


def test_chat_defaults_to_phase1():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns())
    agent.chat([])
    assert "Lock & Key" not in provider.last_system


# ---------------------------------------------------------------------------
# Behavior 9: chat() prepends ContextBuilder output when builder + dungeon given
# ---------------------------------------------------------------------------

class _MockContextBuilder:
    def __init__(self, response=""):
        self._response = response
        self.last_dungeon = None

    def build_system_prompt(self, dungeon, level_id=None):
        self.last_dungeon = dungeon
        return self._response


_SENTINEL_DUNGEON = object()


def test_chat_prepends_context_when_builder_and_dungeon_provided():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    builder = _MockContextBuilder(response="# Setting\nA dark crypt.")
    agent = DungeonWizardAgent(provider=provider, loop_patterns={}, context_builder=builder)
    agent.chat([], dungeon=_SENTINEL_DUNGEON)
    assert "# Setting" in provider.last_system
    assert "A dark crypt." in provider.last_system


def test_chat_no_context_when_dungeon_is_none():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    builder = _MockContextBuilder(response="# Setting\nA dark crypt.")
    agent = DungeonWizardAgent(provider=provider, loop_patterns={}, context_builder=builder)
    agent.chat([])  # dungeon defaults to None
    assert "# Setting" not in provider.last_system


def test_chat_no_context_when_builder_returns_empty():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    builder = _MockContextBuilder(response="")
    agent = DungeonWizardAgent(provider=provider, loop_patterns={}, context_builder=builder)
    agent.chat([], dungeon=_SENTINEL_DUNGEON)
    # System prompt should be the plain phase-1 prompt, no extra prefix
    assert provider.last_system == DungeonWizardAgent.PHASE1_SYSTEM_PROMPT


def test_chat_phase2_also_prepends_context():
    from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent

    provider = _MockProvider(response="ok")
    builder = _MockContextBuilder(response="# Party\nFour adventurers.")
    agent = DungeonWizardAgent(provider=provider, loop_patterns=_make_loop_patterns(), context_builder=builder)
    agent.chat([], phase=2, dungeon=_SENTINEL_DUNGEON)
    assert "# Party" in provider.last_system
    assert "Four adventurers." in provider.last_system
    # Phase 2 content must still be present
    assert "Lock & Key" in provider.last_system
