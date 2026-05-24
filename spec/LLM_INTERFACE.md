# LLM Interface

## Design Goal

Every AI-powered component receives its LLM provider via **dependency injection**.
No component imports a concrete provider class directly. This makes it trivial to:
- Swap Claude for another model or provider
- Use different models for Design Chat vs. DM Chat
- Mock the provider in tests

---

## Core Types — `dungeon_daddy/llm/provider.py`

### `LLMMessage`

```python
from dataclasses import dataclass

@dataclass
class LLMMessage:
    role: str     # "user" | "assistant"
    content: str
```

System prompts are passed separately (as `system: str`), not as messages,
to match the Anthropic API's structure and keep the interface clean for
providers that handle system prompts differently.

---

### `LLMProvider` Protocol

```python
from typing import Protocol, Iterator

class LLMProvider(Protocol):
    """
    Synchronous LLM provider interface.
    All implementations must be safe to call from a background thread.
    """

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """
        Return the full response as a string.
        Blocks until the response is complete.

        Raises LLMError on any API or network failure.
        Never returns an empty string on success.
        """
        ...

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """
        Yield token-level text chunks as they arrive from the API.
        Each yielded string is a partial text token (typically 1–6 characters).
        The concatenation of all yielded strings equals what complete() would return.

        Raises LLMError on any API or network failure (may raise mid-stream).

        Note: stream() is defined in the protocol for future use (token-by-token
        chat bubble rendering). No agent uses it in Phases 1–8. Implement it in
        AnthropicProvider but do not wire it to any UI yet.
        """
        ...

    @property
    def model_id(self) -> str:
        """Human-readable identifier for display in the status bar."""
        ...
```

**Note on `**kwargs`:** The interface intentionally omits `**kwargs`. Parameters
like `temperature` and `top_p` are provider-specific and not part of the
shared contract. If a specific agent needs provider-specific tuning, it should
do so by constructing the provider with those settings baked in at init time,
not by passing them through the protocol.

Any object satisfying this Protocol can be injected — there is no base class
to inherit from.

---

### `LLMError`

A single exception class covers all LLM failures. Define in `provider.py`:

```python
class LLMError(Exception):
    """
    Raised by any LLMProvider implementation on API, network, or auth failure.
    Callers catch LLMError; they do not catch provider-specific exceptions
    (e.g. anthropic.APIError).
    """
    pass
```

**Contract:** Every `LLMProvider` implementation must catch its own SDK exceptions
and re-raise them as `LLMError`. This keeps callers decoupled from the SDK.

---

## Concrete Provider — `dungeon_daddy/llm/anthropic_provider.py`

```python
import anthropic
from dungeon_daddy.llm.provider import LLMProvider, LLMMessage

# Default model constant — update this when the preferred model changes.
# Do not hardcode a model name anywhere else in the codebase.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

class AnthropicProvider:
    """
    Synchronous Anthropic Claude provider.
    Wraps anthropic.Anthropic (sync client).
    Thread-safe: anthropic.Anthropic is safe to share across threads.
    """

    def __init__(
        self,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        api_key: str | None = None,   # falls back to ANTHROPIC_API_KEY env var
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    def complete(self, messages, system="", max_tokens=1024) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e

    def stream(self, messages, system="", max_tokens=1024):
        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            ) as stream:
                yield from stream.text_stream
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e
```

---

## Agents

Agents are thin wrappers that own a system prompt and know how to shape
dungeon context into a message list. They do not know about threads or the UI.

---

### `DungeonWizardAgent` — `dungeon_daddy/llm/agents/wizard_agent.py`

Drives the guided dungeon creation Q&A in Design Mode. Collects all the
information needed before generation begins. Returns a `DungeonBrief` when
the GM confirms they are satisfied.

```python
@dataclass
class DungeonBrief:
    """Structured output of the wizard Q&A. Passed to DungeonGeneratorAgent."""
    title: str
    theme: str
    setting: str
    party: str
    quest: str
    num_levels: int
    primary_loop: str       # LoopPattern key
    sub_loop: str | None    # optional second LoopPattern key
    gm_notes: str           # any extra context from the conversation


class DungeonWizardAgent:
    """
    Guides the GM through dungeon creation via structured Q&A.
    Asks about theme, party, quest, and loop patterns.
    Presents loop pattern options and asks clarifying questions.
    When the GM confirms, returns a DungeonBrief for the generator.
    """

    SYSTEM_PROMPT = """
    You are Dungeon Daddy's creation wizard. Guide the game master through
    designing a new dungeon step by step. Collect:
      1. Dungeon name, theme, and setting (location, history, atmosphere)
      2. Party composition (size, level, class mix)
      3. Main quest or story hook
      4. Number of levels
      5. Primary loop pattern (present the options, explain each briefly)
      6. Optional sub-loop

    Ask one or two questions at a time. Don't overwhelm the GM.
    When you have enough information, summarise the brief and ask for confirmation.
    On confirmation, output a JSON block marked ```brief``` with the DungeonBrief fields.
    """

    def __init__(self, provider: LLMProvider, loop_patterns: dict[str, "LoopPattern"]) -> None:
        self._provider = provider
        self._patterns = loop_patterns

    def chat(self, history: list[LLMMessage]) -> str:
        """Continue the wizard Q&A. Returns the agent's next message."""
        context = self._build_pattern_list()
        return self._provider.complete(
            messages=history,
            system=self.SYSTEM_PROMPT + "\n\n" + context,
            max_tokens=1024,
        )

    def parse_brief(self, response: str) -> "DungeonBrief | None":
        """
        Extract a DungeonBrief from a response containing a ```brief``` block.
        Returns None if no brief block is present (conversation still in progress).
        """
        ...

    def _build_pattern_list(self) -> str:
        """Format the 9 loop patterns as a readable list for the system prompt."""
        ...
```

---

### `DungeonGeneratorAgent` — `dungeon_daddy/llm/agents/generator_agent.py`

Generates dungeon levels one at a time from a confirmed `DungeonBrief`.
Each call produces a `Level` JSON that is validated before being accepted.

```python
class DungeonGeneratorAgent:
    """
    Generates one dungeon level at a time from a DungeonBrief.
    Output is a Level JSON block that can be parsed into a Level model.
    Supports revision: if validate_dungeon() rejects a level, the generator
    is called again with the validation errors as feedback.
    """

    SYSTEM_PROMPT = """
    You are a dungeon architect. Generate one level of a dungeon as JSON.
    The JSON must conform exactly to the Level schema provided.
    Rooms use a grid coordinate system. Connections must be physically plausible
    (adjacent or nearby rooms connected by doors or halls; distant rooms only by
    special connections like teleportation circles or magical passages).
    Apply the specified loop pattern: assign rooms to path_a and path_b.
    Output only a single ```json``` block containing the Level object. No prose.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate_level(
        self,
        brief: "DungeonBrief",
        level_number: int,
        dungeon_so_far: "Dungeon",
        validation_errors: list[str] | None = None,
    ) -> str:
        """
        Generate or revise a level. Returns the raw LLM response (containing
        a ```json``` block). Caller is responsible for parsing and validating.

        If validation_errors is provided, they are included in the prompt as
        feedback for the LLM to fix.
        """
        context = self._build_context(brief, level_number, dungeon_so_far, validation_errors)
        return self._provider.complete(
            messages=[],   # stateless — full context in system prompt
            system=self.SYSTEM_PROMPT + "\n\n" + context,
            max_tokens=4096,
        )

    def parse_level(self, response: str) -> "Level":
        """
        Extract and parse the Level JSON from a ```json``` block in the response.
        Raises ValueError if no valid JSON block is found.
        Raises pydantic.ValidationError if the JSON does not match the Level schema.
        """
        ...

    def _build_context(self, brief, level_number, dungeon_so_far, validation_errors) -> str:
        """
        Build the system prompt context including:
        - DungeonBrief summary
        - Level schema (field names and types)
        - Levels already generated (for stair continuity)
        - Validation errors to fix (if any)
        """
        ...
```

**Generation loop (in `DesignView`):**

```python
MAX_REVISION_ATTEMPTS = 3

def _generate_level(self, level_number: int) -> None:
    errors = None
    for attempt in range(MAX_REVISION_ATTEMPTS):
        response = self._generator_agent.generate_level(
            self._brief, level_number, self._dungeon, errors
        )
        try:
            level = self._generator_agent.parse_level(response)
            result = validate_dungeon_level(level)
            if result.is_valid:
                self._dungeon.levels.append(level)
                return
            errors = result.errors
        except (ValueError, ValidationError) as e:
            errors = [str(e)]
    # After MAX_REVISION_ATTEMPTS, post error to chat and let GM intervene
    self._result_queue.put(LLMResult(
        content="",
        error=f"Level {level_number} could not be generated after {MAX_REVISION_ATTEMPTS} attempts."
    ))
```

---

### `DesignAgent` — `dungeon_daddy/llm/agents/design_agent.py`

Active after generation is complete. Helps the GM refine and edit the dungeon
via free-form chat — add rooms, adjust connections, tweak loop assignments.

```python
class DesignAgent:
    """
    Post-generation design assistant. Helps the GM refine the dungeon
    via conversational chat after the initial generation is complete.
    """

    SYSTEM_PROMPT = """
    You are Dungeon Daddy's design assistant. You help game masters refine
    dungeon crawls using cyclic loop patterns (Lock & Key, Gambit, Foreshadowing,
    etc.). You speak concisely and return structured suggestions.
    When asked to generate or modify dungeon content, respond with a clear
    description of the change and, where relevant, the affected room IDs.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def chat(
        self,
        history: list[LLMMessage],
        dungeon: "Dungeon",
    ) -> str:
        context = self._build_context(dungeon)
        return self._provider.complete(
            messages=history,
            system=self.SYSTEM_PROMPT + "\n\n" + context,
            max_tokens=1024,
        )

    def _build_context(self, dungeon: "Dungeon") -> str:
        # Serialise relevant dungeon metadata as context
        ...
```

---

### `DungeonMasterAgent` — `dungeon_daddy/llm/agents/dm_agent.py`

```python
class DungeonMasterAgent:
    """
    Drives the Play Mode chat. Responds in-character as the dungeon,
    narrating rooms, adjudicating actions, and advancing the story.
    Uses room memory to acknowledge past events and avoid repetition.
    """

    SYSTEM_PROMPT = """
    You are the Dungeon Master for a tabletop dungeon crawl.
    Respond in-character: vivid, atmospheric, concise.
    Use the room and dungeon context to ground every response.
    If play memory is provided for this room, acknowledge what the party has
    already seen or done here — do not describe things they already know.
    Never break character. Never explain the rules.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def respond(
        self,
        history: list[LLMMessage],
        room: "Room",
        level: "Level",
        dungeon: "Dungeon",
        room_memory: str = "",   # markdown memory for current level; "" if none
    ) -> str:
        context = self._build_context(room, level, dungeon, room_memory)
        return self._provider.complete(
            messages=history,
            system=self.SYSTEM_PROMPT + "\n\n" + context,
            max_tokens=512,
        )

    def _build_context(self, room, level, dungeon, room_memory: str) -> str:
        """
        Serialise:
        - Current room name, type, note
        - Level name, ecology
        - Dungeon title and quest
        - Room memory (if non-empty, under a "## Play History" heading)
        """
        ...
```

---

### Context Format — `_build_context()` Conventions

All `_build_context()` methods produce a plain-text string appended to the
system prompt. Use a consistent format so the LLM can parse it reliably:

```
# <Section heading>
<field>: <value>
<field>: <value>
```

**`DungeonMasterAgent._build_context()` example output:**

```
# Current Room
Room: Guard Post (shrine)
Dimensions: 4×3 grid cells
Note: Four guards doze at a stone table. A rusted portcullis blocks the north exit.

# Level
Level: The Sunken Vestibule (Level 1)
Ecology: 4 goblin archers, 1 ogre warlord

# Dungeon
Title: Tomb of the Forgotten King
Quest: Recover the Crown of Kings before the necromantic ceremony at dawn.

# Play History
- 2026-04-23: Party bypassed sleeping guards using a Silence spell.
- 2026-04-23: Rogue pocketed a guard's key ring.
```

If `room_memory` is empty (first visit), omit the `# Play History` section entirely.

**`DesignAgent._build_context()` example output:**

```
# Dungeon
Title: Tomb of the Forgotten King
Theme: Undead • Necromantic
Setting: A collapsed royal tomb beneath a cursed moor.
Party: 4 adventurers • level 3 • mixed
Quest: Recover the Crown of Kings.

# Levels
Level 1 — The Sunken Vestibule: 8 rooms, primary loop: lock_key
Level 2 — Hall of Bound Servants: 7 rooms, primary loop: gambit
Level 3 — The King's Tomb: 6 rooms, primary loop: foreshadow
```

**`DungeonGeneratorAgent._build_context()` example output:**

```
# Dungeon Brief
Title: Tomb of the Forgotten King
Theme: Undead • Necromantic
Party: 4 adventurers • level 3 • mixed
Quest: Recover the Crown of Kings.
Primary loop: lock_key (Lock & Key) — beats: entry, locked door, key location, goal
Sub-loop: none
Total levels: 3

# Generating
Level number: 2 of 3
Previous levels: Level 1 has stair_down connections at rooms 1-G.

# Level Schema (JSON field names and types)
id: int, name: str, summary: str, ecology: str, loop: str,
width: int, height: int, entries: list[Entry],
rooms: list[Room], connections: list[Connection], loops: list[Loop]
Room: id str, num int, name str, x int, y int, w int, h int,
      type str (hall|shrine|lair|vault|stair|study|boss), note str
Connection: from str, to str, type str (door|hall|arch|hole|stair_down|stair_up), note str
Entry: x float, y float, type str (stair_up|stair_down), label str

# Validation Errors to Fix
(none)  ← replaced with actual errors on retry
```

---

### `/remember` Command — Play Mode

The `/remember` command is **not** handled by any agent. It is intercepted by
`PlayView.on_chat_send()` before the LLM thread is spawned:

```python
def on_chat_send(self, text: str) -> None:
    if text.startswith("/remember "):
        event = text[len("/remember "):].strip()
        if event:
            self._repo.append_room_event(
                name=self._dungeon_name,
                level_id=self._current_level.id,
                room_id=self._current_room_id,
                room_name=self._current_room.name,
                event=event,
            )
            self._chat_history.append(ChatMessage(
                role="system",
                content=f"Remembered: {event}",
            ))
            self._rebuild_chat()
        return   # no LLM call

    # ... normal send flow below
```

---

## Swapping Providers

To use a different provider, implement the `LLMProvider` Protocol and inject
it at application startup. Example:

```python
# In window.py or __main__.py
provider = AnthropicProvider(model="claude-haiku-4-5-20251001")
design_agent = DesignAgent(provider=provider)

# Later, swap:
fast_provider = AnthropicProvider(model="claude-haiku-4-5-20251001")
design_view.set_agent(DesignAgent(provider=fast_provider))
```

The UI has no knowledge of which provider is active — it only sees the
`model_id` string for display in the status bar.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | API key for AnthropicProvider. Required at runtime. |

### Startup Key Check

`DungeonDaddyWindow.__init__()` must check for the key before showing any view:

```python
import os

def _check_api_key(self) -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        # Draw a blocking error panel before the game loop starts
        # (or use arcade.gui to show a modal dialog)
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        return False
    return True
```

If the key is missing, the app may still open but LLM features should be
disabled — show an inline notice in the chat panels rather than crashing.

---

## Error Handling Contract

### In Background Threads

LLM calls run in background threads (see `spec/ARCHITECTURE.md — Threading Model`).
`LLMError` is caught in the thread wrapper and posted to the result queue:

```python
def _run_llm(self, text: str) -> None:
    try:
        result = self._agent.chat(...)
        self._result_queue.put(LLMResult(content=result))
    except LLMError as e:
        self._result_queue.put(LLMResult(content="", error=str(e)))
    finally:
        self._llm_busy = False
```

### In the UI

When `result.error` is not None, the chat panel appends a system bubble:

```
⚠ The dungeon is silent. (Rate limit exceeded — try again in a moment.)
```

The error text comes from `result.error`. No dialog, no crash — the session
continues and the user can try again.
