# F-26 · DM Stateful Conversation

## Overview

Dungeon Master chat in Play Mode is currently stateless: every LLM call receives only
the single message the GM just typed, with no history of prior exchanges. The DM also
cannot proactively save observations to room memory — the GM must manually type
`/remember`. This feature adds persistent conversation history within a session and
automatic memory tagging so the DM can record important events itself.

---

## V1 Scope (this phase)

### Feature A — Persistent Conversation History

`PlayView` accumulates all DM turns in `_dm_history: list[LLMMessage]`. Every call to
the DM agent (both chat-send and room-entry auto-describe) passes the full history. When
the history exceeds a 2 000-token budget the oldest user/assistant turn pairs are dropped
until it fits.

**Implementation details:**

| Item | Detail |
|---|---|
| New field | `PlayView._dm_history: list[LLMMessage]` — starts empty |
| Clear on level change | `_dm_history = []` whenever `current_level_idx` changes |
| Compaction strategy | Drop oldest complete turn pairs (user + assistant) until `≤ 2 000` tokens |
| Token estimator | `len(combined_content) // 4` (matches `ContextCompactor._default_count_tokens`) |
| `max_tokens` | Increase `dm_agent.respond()` call from 512 → 1 024 |
| Room-entry | Auto-describe call also appends to and passes `_dm_history` |
| `/clear` command | Resets `_dm_history = []` and posts `"💬 Conversation cleared."` system message |

**History format passed to `dm_agent.respond()`:**

```
[user]      "What traps are in this room?"
[assistant] "The pressure plate near the north door..."
[user]      "We disarm it."
[assistant] "The rogue steps forward..."
[user]      <current message>          ← always last
```

**Files changed:**

- `dungeon_daddy/views/play_view.py` — add `_dm_history`, update `_on_chat_send`,
  `_spawn_dm_thread`, room-click handler, `/clear` command handler
- `dungeon_daddy/llm/agents/dm_agent.py` — increase `max_tokens` 512 → 1 024

---

### Feature B — Auto-Remember via `[REMEMBER]` Tag

The DM `SYSTEM_PROMPT` instructs the model to append `[REMEMBER: one sentence]` to
any response that records a significant event (combat outcome, trap disarmed, NPC
interaction, secret discovered). `PlayView` parses and strips this tag, calls
`append_room_event()` automatically, and posts a `📝 Noted:` system message in chat.

The manual `/remember <text>` command continues to work unchanged.

**Tag format (exactly one per response, optional):**

```
[REMEMBER: The party disarmed the pressure plate near the north door.]
```

**Parsing rules:**

- Regex: `\[REMEMBER:\s*(.+?)\]` (case-insensitive, strip surrounding whitespace)
- If the tag appears mid-response it is extracted and the remainder is rejoined cleanly
- If no tag is present the response is displayed as-is
- The stripped text is passed to `append_room_event()` with the current `room_id` and
  `room_name`
- The `📝 Noted: <text>` system message appears below the DM response in chat

**Updated `SYSTEM_PROMPT` additions (appended to existing prompt):**

```
When something important happens — a trap is sprung or disarmed, a secret is revealed,
an NPC reacts significantly, or the party takes a notable action — append exactly this
tag to the END of your response (never mid-sentence):

  [REMEMBER: one short sentence describing the event]

Use it sparingly: only for facts worth remembering in future sessions.
Do not use it for routine questions or flavour descriptions.
```

**Files changed:**

- `dungeon_daddy/llm/agents/dm_agent.py` — extend `SYSTEM_PROMPT`
- `dungeon_daddy/views/play_view.py` — add `_extract_remember(text) -> tuple[str, str | None]`,
  call it in `on_update()` result handler

---

## Acceptance Criteria

### History

- [ ] After GM sends message A and DM responds, then GM sends message B: the DM call for
      B includes message A and the prior DM response in its history
- [ ] History is cleared when the GM navigates to a different level
- [ ] `/clear` resets history and posts the confirmation system message
- [ ] When history exceeds 2 000 tokens the oldest turn pair is dropped (not split)
- [ ] Room-entry auto-describe calls read from and append to the same `_dm_history`

### Auto-Remember

- [ ] A DM response containing `[REMEMBER: The party found the secret door.]` stores that
      text in `memory/level_N.md` under the current room's section
- [ ] The `[REMEMBER: ...]` tag does not appear in the chat bubble shown to the GM
- [ ] A `📝 Noted: The party found the secret door.` system message appears in chat
- [ ] A DM response with no tag is displayed unchanged
- [ ] More than one `[REMEMBER]` tag in a response: only the first is processed; the
      rest are stripped silently
- [ ] The manual `/remember <text>` command continues to work

---

## Tests to Write First

```
tests/unit/views/test_play_view_history.py
    test_history_accumulates_across_turns
    test_history_cleared_on_level_change
    test_history_compacted_when_over_budget
    test_clear_command_resets_history

tests/unit/views/test_play_view_remember.py
    test_extract_remember_found
    test_extract_remember_not_found
    test_extract_remember_strips_tag_from_response
    test_auto_remember_writes_room_event
    test_auto_remember_posts_system_message

tests/unit/agents/test_dm_agent_history.py
    test_respond_passes_full_history_to_provider
    test_respond_max_tokens_is_1024
```

---

## Out of Scope — V2 Items

The following improvements are deferred to a later phase. They are documented here so
the architecture decisions in V1 don't accidentally block them.

### V2-A · True Tool Use for Remember

Replace the `[REMEMBER]` tag with a first-class LLM tool call using the provider's
function-calling interface. Requires:

- `LLMProvider` Protocol extended with a `complete_with_tools(messages, tools, ...)` method
- `AnthropicProvider` and `OpenAIProvider` implement the new method
- `DMAgent.respond()` passes a `remember_event` tool definition
- `PlayView` handles `tool_use` blocks in the response, routes the call to
  `append_room_event()`, then continues the conversation to get the final text response

**Why deferred:** Requires provider interface changes and divergent Anthropic/OpenAI
implementations. The tag approach delivers the same GM experience with zero provider
changes.

### V2-B · History Persistence Across Sessions

Serialize `_dm_history` to `<dungeon_id>_session.json` alongside `SessionState` so
conversation context survives app restarts.

**Why deferred:** Requires `SessionState` model changes and repository read/write
additions. Session files are already complex; keeping history in-memory for V1 keeps
the scope tight.

### V2-C · Summarization Before Dropping

When history exceeds the 2 000-token budget, send the oldest turns to the LLM for a
one-sentence summary and replace them with `[assistant] Summary: <text>` before
dropping. This preserves semantic content lost by naive drop-oldest.

**Why deferred:** Requires a second synchronous LLM call on the background thread and
adds latency to the user's message. Drop-oldest is good enough for typical session
lengths.

### V2-D · History Across Level Changes

Optionally preserve (compacted) history when the GM navigates between levels, rather
than clearing it entirely. Useful for multi-level sessions where context from earlier
levels matters.

**Why deferred:** Unclear whether cross-level context helps or confuses the DM. Gather
GM feedback on V1 drop behavior first.

---

## Related Files

| File | Role |
|---|---|
| `dungeon_daddy/views/play_view.py` | Chat send, result polling, room-click handler |
| `dungeon_daddy/llm/agents/dm_agent.py` | `SYSTEM_PROMPT`, `respond()`, `max_tokens` |
| `dungeon_daddy/llm/provider.py` | `LLMMessage` dataclass (used as-is, no changes) |
| `dungeon_daddy/data/repository.py` | `append_room_event()` called by auto-remember |
| `dungeon_daddy/llm/context_compactor.py` | Token counting (`len // 4`) reused for history budget |
| `spec/FEATURES.md` | Summary entry F-26 |
