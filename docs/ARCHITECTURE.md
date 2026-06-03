# Dungeon Daddy — Developer Architecture

## Module Layout

```
dungeon_daddy/
├── __main__.py            # Entry point: python -m dungeon_daddy
├── window.py              # DungeonDaddyWindow(arcade.Window) — owns active view + config
├── config.py              # AppConfig dataclass — paths, window size, defaults
│
├── views/
│   ├── design_view.py     # DesignView — dungeon authoring mode
│   └── play_view.py       # PlayView — in-play GM mode
│
├── ui/
│   ├── theme.py           # Colors, font names, layout constants
│   ├── chrome.py          # Menu bar, title bar draw helpers
│   └── panels/
│       ├── chat_panel.py          # Scrollable chat (pure display widget)
│       ├── dungeon_tree_panel.py  # Level/room tree (Design Mode left)
│       ├── inspector_panel.py     # Tabbed right panel
│       ├── loops_panel.py         # Loop pattern library
│       └── map_panel.py           # Map canvas + variant selector
│
├── map/
│   ├── base_renderer.py   # MapRenderer abstract base
│   ├── grid_renderer.py   # Graph-paper style
│   ├── tiles_renderer.py  # Top-down tiles
│   ├── graph_renderer.py  # Abstract node graph
│   └── loop_overlay.py    # Path A/B arcs over any renderer
│
├── rpg/
│   ├── models.py          # ActorState, StressTrack, FalloutRecord, ActionResolution, …
│   ├── dice.py            # d6 pool roller (injectable RNG for tests)
│   ├── actions.py         # Charge-style action roll + outcome classification
│   ├── clocks.py          # Clock create/advance/complete
│   ├── stress.py          # Stress track changes, overflow, recovery
│   ├── fallout.py         # Fallout severity, hooks, dungeon influence side effects
│   └── service.py         # RPGService — orchestration layer called by PlayView
│
├── memory/
│   ├── repository.py      # MemoryRepository — DuckDB data access (no UI, no LLM)
│   ├── markdown_store.py  # Read/write Markdown with YAML front matter
│   ├── retrieval.py       # Deterministic memory search and ranking
│   ├── context_bundle.py  # Builds LLM-ready context bundles with provenance
│   └── sync.py            # SyncReporter — detects DB/Markdown drift
│
├── llm/
│   ├── provider.py        # LLMProvider Protocol + LLMMessage dataclass
│   ├── anthropic_provider.py
│   ├── openai_provider.py # Active provider (gpt-4o, reads OPENAI_API_KEY)
│   └── agents/
│       ├── wizard_agent.py     # Guided dungeon creation Q&A
│       ├── generator_agent.py  # Level-by-level JSON generation
│       ├── design_agent.py     # Post-generation dungeon editing chat
│       └── dm_agent.py         # In-play DM narration (consumes context bundles)
│
└── data/
    ├── models.py          # Pydantic models: Dungeon, Level, Room, Loop, …
    ├── repository.py      # DungeonRepository — JSON + Markdown play memory
    └── migrations/
        ├── 001_rpg_memory_foundation.sql
        ├── 002_dungeon_slug.sql
        └── 003_memory_created_at.sql
```

---

## Dependency Direction

```
views/play_view.py
  -> rpg/service.py
  -> memory/context_bundle.py
  -> llm/agents/dm_agent.py

rpg/service.py
  -> rpg/actions.py, rpg/clocks.py, rpg/stress.py, rpg/fallout.py
  -> memory/repository.py  (via domain event boundary only)

memory/context_bundle.py
  -> memory/retrieval.py
  -> memory/repository.py
  -> memory/markdown_store.py

llm/agents/dm_agent.py
  -> receives ContextBundle — does NOT call MemoryRepository directly
```

**Forbidden imports:**
- `rpg/` must not import `views/` or `ui/`
- `memory/` must not import `views/` or `ui/`
- `llm/agents/` must not import `rpg/service.py` directly
- `ui/panels/` must not write DuckDB directly

---

## Threading Model

Arcade runs a 60 Hz single-threaded game loop. LLM calls run in a daemon-free background thread and post results through a typed queue.

```python
@dataclass
class LLMResult:
    content: str
    error: str | None = None
```

**Send path (main thread):**
1. Guard `self._llm_busy`; drop the send if already waiting.
2. Snapshot `self._chat_history` and dungeon state.
3. Set `self._llm_busy = True`, show typing indicator, start thread.

**Receive path (`on_update`, main thread):**
```python
try:
    result = self._result_queue.get_nowait()
    if result.error:
        append_system_bubble(f"⚠ The dungeon is silent. ({result.error})")
    else:
        append_dm_bubble(result.content)
finally:
    self._llm_busy = False
```

**Rules:**
- One active LLM call per view at a time.
- RPG and memory operations are synchronous (fast enough).
- DuckDB writes go through `MemoryRepository` only — never from threads.
- On `on_hide_view()`: join thread with 3 s timeout, then null the reference.

---

## DB Schema Overview

Campaign state lives in `campaign.duckdb` (DuckDB). Migrations run automatically via `MemoryRepository.initialize_schema(migrations_dir)`.

| Table | Purpose |
|---|---|
| `campaigns` | One row per campaign (id, slug, title, dungeon_slug) |
| `actors` | PCs, NPCs, monsters (id, type, slug, display_name) |
| `action_ratings` | Per-actor action rating (0–3) for each of the 9 actions |
| `stress_tracks` | Per-actor track state (capacity=4, filled=0..4) |
| `abilities` | Per-actor ability key/value pairs |
| `clocks` | Campaign clocks (label, segments, filled, status) |
| `action_resolutions` | History of every action roll outcome |
| `fallout` | Active and resolved fallout records |
| `memory_entries` | Narrative memory (title, summary, importance 1–10) |
| `memory_tags` | Tags attached to memory entries |
| `memory_links` | Directional links between memory entries |
| `domain_events` | Append-only event log (JSON payload) |
| `scenes` | Scene records (location_slug, status) |
| `sessions` | Session metadata |
| `schema_migration` | Applied migration names (idempotency guard) |

The `memory_search_projection` table is a derived cache rebuilt by `tools/rebuild_memory_projection.py`.

---

## Campaign Folder Structure

```
<campaigns_dir>/
  <campaign_slug>/
    dungeon.json          # dungeon design (static blueprint)
    session.json          # play session state
    campaign.duckdb       # MemoryRepository (RPG state + narrative memory)
    memory/               # level play notes (level_N.md) — legacy markdown
    rpg-memory/           # Phase 28+ structured narrative memory
      actors/
      events/
      fallout/
    setting.md            # AI context doc
    party.md
    level_N_design.md
```

---

## Key Invariants

- **LLM is advisory.** Authoritative state lives in DuckDB and Markdown, not in LLM output.
- **Stress track capacity is 4.** The DB default is also 4 (aligned in Phase 32 balance pass).
- **Momentum cap is 6** (enforcement deferred to Phase 33; currently honor-system).
- **Fallout severity** escalates by count of active fallout on the same track (0→minor, 1→moderate, 2+→severe).
- **Font loading** happens once in `DungeonDaddyWindow.__init__()` before any view is shown.
- **UIManager** is owned by each View; never shared between views.
- **Map renderer modules** use `import arcade` (module-level) so tests can patch `arcade.draw_*`.
