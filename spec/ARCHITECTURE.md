# Architecture

## Module Tree

```
dungeon_daddy/
├── __main__.py                  # Entry point: python -m dungeon_daddy
├── window.py                    # DungeonDaddyWindow(arcade.Window)
├── config.py                    # AppConfig: paths, defaults, constants
│
├── views/
│   ├── __init__.py
│   ├── design_view.py           # DesignView(arcade.View)
│   └── play_view.py             # PlayView(arcade.View)
│
├── ui/
│   ├── __init__.py
│   ├── theme.py                 # Color tuples, font names, layout constants
│   ├── chrome.py                # MenuAction dataclass, draw_menu_bar(), draw_title_bar(), dropdown renderer
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── dungeon_tree_panel.py   # Collapsible level/room tree (Design Mode left)
│   │   ├── chat_panel.py           # Scrollable chat + input (shared by both modes)
│   │   ├── inspector_panel.py      # Tabbed right panel (Settings | Loops)
│   │   ├── loops_panel.py          # Loop pattern library + active loop editor
│   │   └── map_panel.py            # Map canvas container + variant selector (Play Mode)
│   └── widgets/
│       ├── __init__.py
│       ├── chat_bubble.py          # Single styled message bubble
│       ├── loop_card.py            # Pattern library card with mini-cycle diagram
│       ├── path_editor.py          # Draggable room chip row for path_a / path_b
│       └── level_stepper.py        # Up/down level navigation control
│
├── map/
│   ├── __init__.py
│   ├── base_renderer.py         # Abstract MapRenderer
│   ├── grid_renderer.py         # GridRenderer — graph-paper style
│   ├── tiles_renderer.py        # TilesRenderer — shaded top-down tiles
│   ├── graph_renderer.py        # GraphRenderer — abstract node graph
│   └── loop_overlay.py          # LoopOverlay — draws path A/B arcs over any renderer
│
├── llm/
│   ├── __init__.py
│   ├── provider.py              # LLMProvider Protocol, LLMMessage dataclass
│   ├── anthropic_provider.py    # AnthropicProvider(LLMProvider)
│   └── agents/
│       ├── __init__.py
│       ├── wizard_agent.py      # DungeonWizardAgent — guided dungeon creation Q&A
│       ├── generator_agent.py   # DungeonGeneratorAgent — level-by-level JSON generation
│       ├── design_agent.py      # DesignAgent — post-generation dungeon editing chat
│       └── dm_agent.py          # DungeonMasterAgent — in-play DM responses
│
└── data/
    ├── __init__.py
    ├── models.py                # All Pydantic models (see DATA_MODEL.md)
    ├── repository.py            # DungeonRepository — load/save JSON + memory markdown
    └── samples/
        └── tomb_of_the_forgotten_king.json
```

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── data/
│   │   ├── test_models.py
│   │   └── test_repository.py
│   ├── llm/
│   │   ├── test_provider.py
│   │   ├── test_design_agent.py
│   │   └── test_dm_agent.py
│   ├── map/
│   │   ├── test_grid_renderer.py
│   │   ├── test_tiles_renderer.py
│   │   ├── test_graph_renderer.py
│   │   └── test_loop_overlay.py
│   └── ui/
│       └── test_theme.py
└── integration/
    ├── __init__.py
    ├── test_dungeon_persistence.py
    └── test_llm_integration.py
```

---

## Component Responsibilities

### `window.py` — `DungeonDaddyWindow`

Subclass of `arcade.Window`. Owns:
- The active `arcade.View` (Design or Play)
- The loaded `Dungeon` object passed down to both views
- Mode-switching logic (`switch_to_design()`, `switch_to_play()`)
- The single `AppConfig` instance

The window does **not** own the UI panels — each View owns its own `UIManager`.

---

### `views/design_view.py` — `DesignView`

Active when the user is authoring a dungeon. Owns:
- A `UIManager` containing: `DungeonTreePanel` (left), `ChatPanel` (centre),
  `InspectorPanel` (right — tabs: Settings, Loops)
- The `DesignAgent` instance (receives `LLMProvider` at construction)
- Editable `loops_by_level` state (dict of level_id → list[Loop])
- `active_loop_id` — which loop is currently highlighted in tree + map
- `_chat_history: list[ChatMessage]` — the in-memory transcript for this session
- `_result_queue` and `_llm_busy` — see Threading Model

DesignView does not render the dungeon map. The DungeonTree panel is a text-based
tree showing levels and rooms, coloured by loop path membership.

---

### `views/play_view.py` — `PlayView`

Active during a play session. Owns:
- A `UIManager` containing: `ChatPanel` (left), `MapPanel` + `LevelStepper` (right)
- The `DungeonMasterAgent` instance
- Session state: `current_level_idx`, `current_room_id`, `visited_rooms`, `active_loop_id`
- The active `MapRenderer` instance (swapped when variant changes)
- `_chat_history: list[ChatMessage]` — the in-memory transcript for this session
- `_result_queue` and `_llm_busy` — see Threading Model

PlayView draws the map directly to the Arcade canvas each frame and overlays
the `UIManager` on top.

---

### `ChatPanel` — Ownership and State

`ChatPanel` is a **widget class** (`dungeon_daddy/ui/panels/chat_panel.py`) that
is instantiated **once per view** — `DesignView` has its own instance, `PlayView`
has its own. They are not shared.

Chat history is **not stored inside `ChatPanel`**. The panel is a pure display
widget: it takes a list of `ChatMessage` objects and renders them. The list is
owned by the view (`self._chat_history`), which passes it into the panel on
every rebuild and whenever a new message arrives.

**Transcript initialization and persistence contract:**

Each view owns the transcript for its mode. The `SessionState` object is the
durable store. The contract is:

1. `DesignView` initialises `self._chat_history` from `session.design_transcript`
   in `on_show_view()`.
2. `PlayView` initialises `self._chat_history` from `session.play_transcript`
   in `on_show_view()`.
3. Before `on_hide_view()` completes, the view writes `self._chat_history` back
   to the corresponding `session` field:
   ```python
   # In DesignView.on_hide_view():
   self._session.design_transcript = list(self._chat_history)
   # In PlayView.on_hide_view():
   self._session.play_transcript = list(self._chat_history)
   ```
4. `DungeonRepository.save_session()` is called after every GM message send and
   on mode switch, so transcripts survive crashes.

Neither view passes the other's transcript to its `ChatPanel`. `DesignView` never
sees `play_transcript` and vice-versa.

---

### `map/base_renderer.py` — `MapRenderer`

Abstract base class. Subclasses implement:

```python
def draw(
    self,
    level: Level,
    current_room_id: str,
    visited: set[str],
    region: tuple[float, float, float, float],  # left, bottom, width, height
) -> None: ...
```

All geometry uses `arcade.draw_*` primitives. No external rendering library.
Receives a `region` so it can be positioned inside the map panel.

---

### `map/loop_overlay.py` — `LoopOverlay`

Draws teal (path A) and violet (path B) arcs over the current map, given:
- The active `Loop` object
- The same `region` and `Level` passed to the renderer

Called after `MapRenderer.draw()` so arcs appear on top.

---

### `llm/provider.py` — `LLMProvider` Protocol

See `spec/LLM_INTERFACE.md` for the full interface definition.

---

### `data/repository.py` — `DungeonRepository`

Responsible for reading and writing `Dungeon` objects to JSON files in the
user data directory. Never accessed directly by UI code — views call it
through the window.

---

## Threading Model

Arcade runs a single-threaded game loop. LLM API calls block for seconds.
To keep the UI responsive, LLM calls run in background threads that post
results back to the game loop via a thread-safe queue.

### Queue Type

Each view owns a single result queue:

```python
import queue
from dataclasses import dataclass

@dataclass
class LLMResult:
    content: str               # the response text
    error: str | None = None   # set if the call failed, None on success
```

```python
# In DesignView / PlayView
self._result_queue: queue.Queue[LLMResult] = queue.Queue()
```

Using a typed dataclass (not a bare string) means errors and successes travel
through the same channel and the UI can distinguish them without side-effects.

### Send / Receive Lifecycle

```
Main Thread (Arcade game loop, ~60 Hz)
│
├── on_update(delta_time) ──► try: result = self._result_queue.get_nowait()
│                              except queue.Empty: pass
│                              if result.error: show_error_in_chat(result.error)
│                              else: append_dm_bubble(result.content)
│                                    clear_typing_indicator()
│
└── on_chat_send(text) ──► guard: if self._llm_busy: return  # drop if already waiting
                            self._llm_busy = True
                            # Append GM message to history BEFORE spawning thread
                            # so the thread captures the complete conversation.
                            self._chat_history.append(ChatMessage(role="gm", content=text))
                            show_typing_indicator()
                            # Snapshot the history and dungeon state for the thread.
                            # Pass copies so mutations in the main thread don't
                            # affect the in-flight call.
                            history_snapshot = list(self._chat_history)
                            # Deep copy the dungeon so the generator thread works on
                            # a stable snapshot even if the main thread modifies state.
                            import copy
                            dungeon_snapshot = copy.deepcopy(self._dungeon)
                            thread = Thread(
                                target=self._run_llm,
                                args=(history_snapshot, dungeon_snapshot),
                                daemon=False,
                            )
                            self._active_thread = thread
                            thread.start()

Background Thread
└── self._run_llm(history: list[ChatMessage], dungeon: Dungeon):
      # Convert ChatMessage history → LLMMessage list for the provider.
      # Exclude system dividers (role="system"); map gm→user, dm→assistant.
      llm_messages = [
          LLMMessage(role="user" if m.role == "gm" else "assistant", content=m.content)
          for m in history if m.role in ("gm", "dm")
      ]
      try:
          result = agent.chat(messages=llm_messages, dungeon=dungeon)  # blocks here
          self._result_queue.put(LLMResult(content=result))
      except LLMError as e:
          self._result_queue.put(LLMResult(content="", error=str(e)))
      finally:
          self._llm_busy = False
```

### Rules

- **One active LLM call at a time per view.** If `self._llm_busy` is True when
  the user sends, ignore the send (the UI should grey out the send button).
- **Non-daemon threads** (`daemon=False`). On window close, join the active
  thread with a 3-second timeout, then null the reference:
  ```python
  def on_hide_view(self):
      if self._active_thread and self._active_thread.is_alive():
          self._active_thread.join(timeout=3.0)
      self._active_thread = None
      self.manager.disable()
  ```
- **`queue.get_nowait()`** — never block the main thread. If the queue is empty,
  skip. Results arrive within the next frame cycle (~16 ms at 60 Hz).
- **Error handling in the UI**: if `result.error` is set, append a system message
  to the chat: `"⚠ The dungeon is silent. ({error})"` where `{error}` is the
  value of `result.error`. This is the canonical error format — use it everywhere.
- **Thread reference cleanup**: always set `self._active_thread = None` after join.

---

## Data Flow — Design Mode

```
User types in ChatPanel
  └──► DesignView.on_send()
         └──► Thread: DesignAgent.chat(messages, dungeon)
                └──► LLMProvider.complete(...)
                       └──► result_queue → ChatPanel.append_message()
```

Changes to loops (pattern applied, rooms reassigned) are held in
`DesignView.loops_by_level` dict. They are written to the dungeon and
persisted only when the user explicitly saves.

---

## Data Flow — Design Mode (Wizard Phase)

```
DesignView opens (no dungeon loaded)
  └──► wizard_mode = True
         └──► DungeonWizardAgent drives the chat:
                collects meta (title, theme, setting, party, quest)
                presents loop pattern options, collects choice
                asks clarifying questions
                GM reviews and confirms DungeonBrief
                  └──► wizard_mode = False → generation_mode = True
```

## Data Flow — Design Mode (Generation Phase)

```
GM confirms DungeonBrief
  └──► DesignView enters generation_mode
         └──► For each level 1..N:
                Thread: DungeonGeneratorAgent.generate_level(brief, level_idx, dungeon_so_far)
                  └──► LLMProvider.complete(...)
                         └──► result_queue → parse Level JSON
                                └──► validate_dungeon() on new level
                                       if invalid: re-prompt LLM to fix
                                       if valid: append level to Dungeon
                                                 show level in DungeonTreePanel
                                                 GM reviews — may request changes
         └──► Cross-level traversal check (stair consistency)
         └──► Switch to editing mode (DesignAgent for refinement chat)
```

## Data Flow — Play Mode

```
User types in ChatPanel  OR  clicks room on map
  └──► PlayView.on_send() / on_room_click()
         ├──► if message starts with "/remember ":
         │      extract event text
         │      DungeonRepository.append_room_event(dungeon_id, level_id, room_id, event)
         │      append system bubble "Remembered: <event>"
         │      (no LLM call)
         └──► otherwise:
                updates session state (current_room, visited)
                room_memory = DungeonRepository.load_room_memory(dungeon_id, level_id)
                Thread: DungeonMasterAgent.respond(messages, room, level, dungeon, room_memory)
                  └──► LLMProvider.complete(...)
                         └──► result_queue → ChatPanel.append_message()
```

---

## Memory Layer

The dungeon data model has two distinct layers with different lifecycles:

### JSON (Blueprint — static)

`<dungeon_stem>.json` — the dungeon as designed. Rooms, connections, dimensions,
loop assignments, starting state. Created during the wizard + generation flow.
Never changed by play events.

### Markdown (Memory — dynamic)

`<dungeon_stem>_memory/level_<N>.md` — one file per level, created on first
`/remember` event. Accumulates the play history of every room: what the party
did, what changed, what was taken or triggered.

**File layout:**

```
dungeons/
├── tomb_of_the_forgotten_king.json
├── tomb_of_the_forgotten_king_session.json
└── tomb_of_the_forgotten_king_memory/
    ├── level_1.md
    ├── level_2.md
    └── level_3.md
```

**Level memory file format:**

```markdown
# Level 1 — The Sunken Vestibule: Play Memory

## Room 1-A — Flooded Entry
- 2026-04-23: Party entered cautiously. Rogue found a corroded iron key in the drain.
- 2026-04-23: Fighter triggered the pressure plate. Lost 4 HP.

## Room 1-C — Guard Post
- 2026-04-23: Party bypassed sleeping guards using Silence spell.
```

**Recording events — `/remember` command:**

In Play Mode, the GM types `/remember <event text>` in the chat input. `PlayView`
intercepts this before it reaches the LLM thread:

1. Strips the `/remember ` prefix.
2. Calls `DungeonRepository.append_room_event()` with the current room and level.
3. Appends a system bubble to the chat: `"Remembered: <event text>"`.
4. No LLM call is made for `/remember` commands.

**Editing memory:**

Room memory can be edited directly. `PlayView` exposes an "Edit Memory" button
(visible when the current room has memory). Clicking it opens the level memory
file content in a `UITextArea` overlay — the GM edits the raw markdown and saves.
`DungeonRepository.save_room_memory()` overwrites the file.

**DM Agent access:**

Before each `DungeonMasterAgent.respond()` call, `PlayView` loads the memory for
the current level and passes it as `room_memory: str`. The agent uses it to avoid
re-describing things the party already know and to acknowledge past events.

---

## Configuration — `config.py`

`AppConfig` is a plain Python dataclass (not Pydantic, to avoid an extra
import). Constructed once in `__main__.py` and passed to `DungeonDaddyWindow`.

```python
from dataclasses import dataclass, field
from pathlib import Path
from platformdirs import user_data_path

@dataclass
class AppConfig:
    user_data_dir: Path = field(
        default_factory=lambda: user_data_path("DungeonDaddy", appauthor=False)
    )
    window_width: int = 1400
    window_height: int = 900
    window_title: str = "Dungeon Daddy"
    default_map_variant: str = "grid"

    @property
    def dungeons_dir(self) -> Path:
        return self.user_data_dir / "dungeons"

    def ensure_dirs(self) -> None:
        """Create user data directories if they do not exist."""
        self.dungeons_dir.mkdir(parents=True, exist_ok=True)
```

`ensure_dirs()` is called once at startup before the window opens.
All path construction uses `pathlib.Path` — never string concatenation.

---

## Arcade Integration

### UIManager Lifetime

Each `arcade.View` subclass creates its own `UIManager` in `on_show_view()` and
disables it in `on_hide_view()`:

```python
class DesignView(arcade.View):
    def on_show_view(self):
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self._build_ui()   # add widgets to self.manager

    def on_hide_view(self):
        self.manager.disable()

    def on_draw(self):
        self.clear()
        # draw chrome (menu bar, title bar) first
        draw_menu_bar(self.window)
        draw_title_bar(self.window, mode="design", on_mode=self.window.switch_mode)
        # then let UIManager draw panels on top
        self.manager.draw()
```

**Never share a `UIManager` between views.** Each view owns its own instance.

### Font Loading

All custom fonts are loaded **once** in `DungeonDaddyWindow.__init__()` before
any view is shown:

```python
from pathlib import Path
import arcade

FONT_DIR = Path(__file__).parent / "assets" / "fonts"

def load_fonts():
    arcade.load_font(str(FONT_DIR / "IMFellEnglish-Regular.ttf"))
    arcade.load_font(str(FONT_DIR / "IMFellEnglish-Italic.ttf"))
    arcade.load_font(str(FONT_DIR / "IMFellEnglishSC-Regular.ttf"))
    arcade.load_font(str(FONT_DIR / "JetBrainsMono-Regular.ttf"))
    arcade.load_font(str(FONT_DIR / "JetBrainsMono-Medium.ttf"))
    arcade.load_font(str(FONT_DIR / "Inter-Regular.ttf"))
    arcade.load_font(str(FONT_DIR / "Inter-Medium.ttf"))
    arcade.load_font(str(FONT_DIR / "Inter-Bold.ttf"))
```

Font files are bundled under `dungeon_daddy/assets/fonts/`. They must be
downloaded from Google Fonts and committed to the repository. See
`spec/TECH_STACK.md` → Asset Bundling.

### Chrome Drawing

The menu bar and title bar are drawn via helper functions in `dungeon_daddy/ui/chrome.py`.
They are called at the **start of every `on_draw()`** in both views, before
`self.manager.draw()`. They use `arcade.draw_*` primitives directly — they are
not part of the UIManager widget tree.

Chrome height constants:
- Menu bar: 26 px — positioned at `window.height - 26` (top of window)
- Title bar: 44 px — positioned at `window.height - 70`

Views must offset their UIManager panel content by `CHROME_MENUBAR_HEIGHT + CHROME_TITLEBAR_HEIGHT = 70 px`
from the top of the window.

### Import Style for Renderers

Map renderer modules **must** use module-level imports:

```python
import arcade   # correct — enables mocker.patch("arcade.draw_rect_filled")
```

**Never** use:
```python
from arcade import draw_rect_filled  # wrong — breaks mocker.patch("arcade.draw_rect_filled")
```

This is required so unit tests can patch `arcade.draw_*` functions without
opening a display window. See `spec/TESTING.md`.

### Window Resize

Panel widths defined in `spec/VISUAL_DESIGN.md` (`PANEL_TREE_WIDTH`, etc.) are
**minimum widths**. On resize, the centre panel grows and the fixed-width panels
stay constant. Layouts should be rebuilt in `on_resize(width, height)` by
calling `self._build_ui()` again after clearing the UIManager.

**State preservation across rebuild:**

Before clearing the `UIManager` in `on_resize()`, save any transient UI state
that must survive the rebuild:

```python
def on_resize(self, width: int, height: int) -> None:
    # Save before clearing
    scroll_pos = self._chat_panel.scroll_position if self._chat_panel else 0
    # Rebuild
    self.manager.clear()
    self._build_ui()
    # Restore
    if self._chat_panel:
        self._chat_panel.scroll_to(scroll_pos)
```

Do not attempt to preserve text-selection state — it resets on rebuild and that
is acceptable. Flickering on resize is acceptable; maintain 60 Hz during normal
play.

### `on_update` Signature

```python
def on_update(self, delta_time: float) -> None:
    """Called ~60 times/second. Check the LLM result queue here."""
    try:
        result = self._result_queue.get_nowait()
        ...
    except queue.Empty:
        pass
```

`delta_time` is the time in seconds since the last update — always accept it
even if not used.
