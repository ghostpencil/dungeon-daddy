# F-30 · Knowledge Graph

## Overview

Dungeon Daddy's DM narration is currently anchored to flat markdown — room descriptions,
context docs, and a memory file per level. This works, but the AI has no awareness of
*relationships*: who lives where, which factions are in conflict, what the party has
already discovered about an NPC, or how a world event in one room affects another.

The Knowledge Graph adds a structured relational layer to every dungeon. It stores
entities (NPCs, Factions, Items, Party Members, World Events) and the edges between
them. The DM agent queries this graph on every response, receiving structured world
state rather than guessing from prose. The result is coherent, drift-free narration
that remembers — across rooms, across levels, across sessions.

This feature serves both modes:
- **Design Mode** — the GM builds and edits the world graph as part of dungeon authoring
- **Play Mode** — the graph is queried to give the DM agent full relational context;
  it is updated automatically as the party discovers entities and events occur

---

## V1 Scope

### Feature A — Graph Data Models

New Pydantic models added to `dungeon_daddy/data/models.py`:

**`NPC`**

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID (`npc_<slug>`) |
| `name` | `str` | Display name |
| `description` | `str` | One-paragraph prose description for the DM |
| `role` | `str` | e.g. `"guard"`, `"merchant"`, `"cultist"` |
| `faction_id` | `str \| None` | FK → `Faction.id` |
| `home_room_id` | `str \| None` | FK → `Room.id` (where they are found by default) |
| `current_room_id` | `str \| None` | Tracked during play; starts equal to `home_room_id` |
| `disposition` | `str` | `"friendly"`, `"neutral"`, `"hostile"` |
| `discovered` | `bool` | `False` until party interacts with this NPC |
| `knows` | `dict[str, str]` | `npc_id → relationship` (`"ally"`, `"enemy"`, `"neutral"`) |
| `notes` | `str` | GM freeform notes |

**`Faction`**

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID (`fac_<slug>`) |
| `name` | `str` | Display name |
| `description` | `str` | Goals, history, alignment |
| `controls_room_ids` | `list[str]` | Rooms this faction dominates |
| `disposition` | `str` | `"friendly"`, `"neutral"`, `"hostile"` toward the party |
| `notes` | `str` | GM freeform notes |

**`WorldItem`**

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID (`item_<slug>`) |
| `name` | `str` | Display name |
| `description` | `str` | What it is and why it matters |
| `room_id` | `str \| None` | Where it is located (null if carried) |
| `owner_id` | `str \| None` | NPC or `"party"` if carried |
| `discovered` | `bool` | `False` until party finds it |
| `notes` | `str` | GM freeform notes |

**`WorldEvent`**

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID (`evt_<uuid4 short>`) |
| `description` | `str` | One-sentence summary of what happened |
| `room_id` | `str \| None` | Where it occurred |
| `involved_npc_ids` | `list[str]` | NPCs involved |
| `involved_item_ids` | `list[str]` | Items involved |
| `turn` | `int` | Turn counter at time of event (monotonically increasing) |

**`PartyMember`**

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID (`pc_<slug>`) |
| `name` | `str` | Character name |
| `class_name` | `str` | e.g. `"Rogue"`, `"Wizard"` |
| `notes` | `str` | GM notes on this character's hooks, motivations, quirks |

**`KnowledgeGraph`** (top-level container, stored per dungeon)

```python
class KnowledgeGraph(BaseModel):
    npcs:    list[NPC]         = Field(default_factory=list)
    factions: list[Faction]    = Field(default_factory=list)
    items:   list[WorldItem]   = Field(default_factory=list)
    events:  list[WorldEvent]  = Field(default_factory=list)
    party:   list[PartyMember] = Field(default_factory=list)
    turn:    int               = 0
```

---

### Feature B — Graph Storage + Repository

The graph lives at `{data_dir}/{dungeon_name}/knowledge_graph.json` (indent=2).
It is loaded/saved independently of the dungeon JSON — partial saves are safe.

**New `DungeonRepository` methods:**

| Method | Signature | Notes |
|---|---|---|
| `load_graph` | `(dungeon_name: str) → KnowledgeGraph` | Returns empty graph if file missing |
| `save_graph` | `(dungeon_name: str, graph: KnowledgeGraph) → None` | Atomic write |

Mutation helpers (operate on an in-memory `KnowledgeGraph`, caller saves):

| Helper | Purpose |
|---|---|
| `graph_add_event(graph, description, room_id, npc_ids, item_ids) → WorldEvent` | Append event, increment `graph.turn` |
| `graph_set_discovered(graph, entity_id) → None` | Sets `discovered=True` on NPC or WorldItem by ID |
| `graph_move_npc(graph, npc_id, room_id) → None` | Updates `current_room_id` |
| `graph_transfer_item(graph, item_id, owner_id, room_id) → None` | Moves item ownership |

---

### Feature C — Graph Context Query + DM Integration

`ContextBuilder` gains a new method:

```python
def build_graph_context(
    self,
    graph: KnowledgeGraph,
    room_id: str,
    level: Level,
) -> str:
```

This assembles a structured markdown block injected into the DM system prompt:

```
## World State — Current Room

NPCs present: Aldric the Innkeeper (friendly, Merchant Guild)
  - Knows: Sister Vael [enemy]
  - Status: undiscovered by party

Faction control: Merchant Guild (neutral to party)

Items here: Sealed Letter (undiscovered), Lantern (discovered)

Recent events in this room:
  - Turn 3: The party questioned a nervous guard (guard fled)
```

Only entities relevant to the current room are included. Undiscovered entities are
listed with a GM-only marker — the DM knows they exist but describes them naturally
without revealing meta-information to players.

**`DungeonMasterAgent.respond()` signature update:**

```python
def respond(
    self,
    history: list[LLMMessage],
    room: Room,
    level: Level,
    dungeon: Dungeon,
    room_memory: str = "",
    active_loop: Loop | None = None,
    graph_context: str = "",          # ← new
) -> str:
```

`graph_context` is appended to the system prompt after the room memory block.

---

### Feature D — Play Mode Graph Updates

When the party interacts with the world during Play Mode, `PlayView` updates the graph:

| Trigger | Graph update |
|---|---|
| DM `[REMEMBER]` tag fired | `graph_add_event(...)` with current room + turn |
| `/discover <npc_id>` command | `graph_set_discovered(graph, npc_id)` |
| `/move <npc_id> <room_id>` command | `graph_move_npc(graph, npc_id, room_id)` |
| `/give <item_id> party` command | `graph_transfer_item(graph, item_id, "party", None)` |

The graph is saved to disk after every mutation.
The turn counter increments on every DM response (room entry or chat send).

---

### Feature E — Design Mode: World Tab

`InspectorPanel` gains a third tab: **World**.

The World tab renders three collapsible sections:

**NPCs** — one row per NPC: name chip (colored by faction), role label, home room.
Clicking a row opens an edit overlay (same `UITextArea` pattern as context docs).

**Factions** — one row per faction: name, disposition chip, room count.
Clicking opens edit overlay.

**Items** — one row per item: name, location, discovered status.
Clicking opens edit overlay.

**Party** — one row per party member: name, class. Clicking opens edit overlay.

A `+` chip at the section header creates a new blank entity of that type.

The GM can build out the world graph in Design Mode before play begins.

---

## Acceptance Criteria

### Data Model

- [ ] `KnowledgeGraph`, `NPC`, `Faction`, `WorldItem`, `WorldEvent`, `PartyMember`
      all round-trip through `model_dump(mode="json")` → re-validate → equal
- [ ] Empty graph is returned when no file exists (no exception)
- [ ] `graph_add_event` appends to `events` and increments `turn`
- [ ] `graph_set_discovered` sets `discovered=True` on correct entity by ID

### Storage

- [ ] `save_graph` writes valid JSON with `indent=2` to correct path
- [ ] `load_graph` returns the saved graph unchanged after round-trip
- [ ] Saving graph does not touch the dungeon JSON or session JSON

### DM Integration

- [ ] `build_graph_context` includes only NPCs whose `home_room_id` or
      `current_room_id` matches the queried room
- [ ] Undiscovered entities appear in the context block (GM-only visibility marker)
- [ ] `DungeonMasterAgent.respond()` includes graph context in system prompt
      when `graph_context` is non-empty; system prompt unchanged when empty
- [ ] No real API calls in unit tests (provider mocked)

### Play Mode Updates

- [ ] `[REMEMBER]` tag fires `graph_add_event` with current room and turn
- [ ] Turn counter increments on each DM response
- [ ] Graph is saved to disk after each mutation
- [ ] `/discover`, `/move`, `/give` commands update graph correctly

### Design Mode UI

- [ ] World tab renders without crash when graph is empty
- [ ] World tab renders NPC rows when graph has NPCs
- [ ] `+` chip creates a new blank NPC/Faction/Item entry
- [ ] Edit overlay opens pre-filled with entity data; save persists; cancel discards
- [ ] `pytest tests/unit/` green (621+ tests)

---

## Tests to Write First

```
tests/unit/data/test_knowledge_graph.py
    test_knowledge_graph_empty_default
    test_knowledge_graph_round_trip
    test_graph_add_event_appends_and_increments_turn
    test_graph_set_discovered_npc
    test_graph_set_discovered_item
    test_graph_move_npc_updates_room
    test_graph_transfer_item_to_party

tests/unit/data/test_repository_graph.py
    test_load_graph_missing_file_returns_empty
    test_save_and_load_graph_round_trip
    test_save_graph_does_not_touch_dungeon_json

tests/unit/llm/test_context_builder_graph.py
    test_build_graph_context_includes_npcs_in_room
    test_build_graph_context_excludes_npcs_in_other_rooms
    test_build_graph_context_marks_undiscovered
    test_build_graph_context_empty_when_no_entities

tests/unit/llm/test_dm_agent_graph.py
    test_respond_includes_graph_context_in_system_prompt
    test_respond_graph_context_empty_string_unchanged_prompt

tests/unit/views/test_play_view_graph.py
    test_remember_tag_adds_world_event
    test_turn_increments_on_dm_response
    test_discover_command_sets_discovered
    test_graph_saved_after_mutation

tests/unit/ui/test_inspector_panel_world_tab.py
    test_world_tab_renders_without_crash_empty_graph
    test_world_tab_renders_npc_rows
    test_world_tab_plus_chip_creates_npc
```

---

## Out of Scope — V2 Items

### V2-A · Wizard Auto-Seeding

During dungeon generation, the `DungeonGeneratorAgent` produces a `knowledge_graph`
JSON block alongside each level JSON. The generator prompt instructs the model to
populate NPCs, factions, and key items that fit the dungeon's theme and loop structure.

**Why deferred:** Requires generator prompt changes and a second parse step.
V1 lets the GM build the graph manually — which may produce higher-quality results
for detail-oriented GMs anyway.

### V2-B · Visual Graph Editor

A dedicated canvas view (separate from `InspectorPanel`) renders the graph as a
force-directed node diagram. Nodes are colored by type; edges are drawn as labeled
arcs. GM can drag nodes, click edges to edit relationship labels.

**Why deferred:** Requires a graph layout algorithm and a new view — substantial UI
work. The tabular World tab delivers full edit capability without it.

### V2-C · NPC Dialogue Agent

A dedicated `NPCAgent` handles NPC-specific dialogue turns when the party speaks
directly to a named NPC. It receives the NPC's `description`, `knows` relationships,
and faction allegiance, and responds in character. The DM agent routes to it when
the party addresses an NPC by name.

**Why deferred:** Requires agent routing logic and per-NPC conversation history.
V1 lets the DM agent narrate NPC responses using graph context.

### V2-D · Cross-Room Event Propagation

When a significant event occurs (e.g. a faction leader is killed), the graph can
flag downstream rooms and NPCs as "affected." The DM agent receives a brief
propagation summary when entering affected rooms.

**Why deferred:** Requires a propagation rule engine. V1 manual `/remember` tagging
covers the same need with GM control.

### V2-E · Narrative Play Mode

A dedicated `NarrativePlayView` gives a single player a solo dungeon crawl experience.
The graph is the game state: the player's position is tracked as a party member node,
actions are resolved by the DM agent using graph context, and consequences update the
graph automatically. No dice — all resolution is narrative and contextual.

**Why deferred:** Requires a new view and a player-input action parser. The Knowledge
Graph (V1) is the prerequisite; once the graph is stable this mode becomes feasible.

---

## Related Files

| File | Role |
|---|---|
| `dungeon_daddy/data/models.py` | New graph models added here |
| `dungeon_daddy/data/repository.py` | `load_graph`, `save_graph`, mutation helpers |
| `dungeon_daddy/llm/context_builder.py` | `build_graph_context` method |
| `dungeon_daddy/llm/agents/dm_agent.py` | `graph_context` param added to `respond()` |
| `dungeon_daddy/views/play_view.py` | Graph load, turn counter, command handlers, save-on-mutate |
| `dungeon_daddy/ui/panels/inspector_panel.py` | World tab added |
| `spec/FEATURES.md` | Summary entry F-30 |
