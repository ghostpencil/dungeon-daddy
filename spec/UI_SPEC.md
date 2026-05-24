# UI Specification

## Window

| Property | Value |
|---|---|
| Minimum size | 1400 × 900 px |
| Default size | 1400 × 900 px |
| Resizable | Yes |
| Style | Standard OS window (not borderless) |
| Background | `BG_0` (see VISUAL_DESIGN.md) |

The OS title bar is used as-is. The app draws its own **menu bar** and **title bar**
as Arcade UI elements immediately below the OS title bar. Together they form the
"chrome" visible in the web prototype.

---

## Chrome (drawn inside the Arcade window)

### Menu Bar — height 26 px, pinned to top

Drawn as a filled rectangle (`BG_1` with slight gradient). Contains from left to right:

- Arcane sigil SVG-equivalent (drawn with Arcade lines/circles): 14×14 px, 14 px margin
- App name: "Dungeon Daddy" — `FONT_SERIF`, 13 px, bold, `INK_1`
- Menu items: File · Edit · Dungeon · Play · View · Window · Help — `FONT_UI`, 13 px, `INK_2`
- Right side: moon phase text `◐ moon waxing · d3 until new` + clock — `FONT_MONO`, 11 px, `INK_3`

### Menu Action System

All menu items — including those not yet implemented — must be wired through a
**central menu action registry**. This ensures future menu items are added by
registering an action, not by modifying the chrome drawing code.

Define `MenuAction` in `dungeon_daddy/ui/chrome.py`:

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class MenuAction:
    label: str                        # display text in the menu
    handler: Callable[[], None]       # called when item is clicked
    enabled: bool = True              # greyed out when False
    implemented: bool = True          # False = shown but logs "not yet implemented"
```

`DungeonDaddyWindow` builds and owns the full menu definition at startup:

```python
self._menu: dict[str, list[MenuAction]] = {
    "File": [
        MenuAction("New",   self.new_dungeon),
        MenuAction("Open",  self.open_dungeon),
        MenuAction("Save",  self.save_dungeon),
    ],
    "Edit": [
        MenuAction("Undo",  self._nyi, implemented=False),
        MenuAction("Redo",  self._nyi, implemented=False),
    ],
    "Dungeon": [
        MenuAction("Validate",       self._nyi, implemented=False),
        MenuAction("Generate Level", self._nyi, implemented=False),
    ],
    "Play": [
        MenuAction("Switch to Play", lambda: self.switch_mode("play")),
        MenuAction("Switch to Design", lambda: self.switch_mode("design")),
    ],
    "View": [
        MenuAction("Map: Grid",   lambda: self.set_map_variant("grid"),  implemented=False),
        MenuAction("Map: Tiles",  lambda: self.set_map_variant("tiles"), implemented=False),
        MenuAction("Map: Graph",  lambda: self.set_map_variant("graph"), implemented=False),
    ],
    "Window": [
        MenuAction("Minimise", self._nyi, implemented=False),
    ],
    "Help": [
        MenuAction("About", self._nyi, implemented=False),
    ],
}

def _nyi(self) -> None:
    """Not yet implemented — log only, no crash, no dialog."""
    import logging
    logging.getLogger(__name__).info("Menu action not yet implemented")
```

### Menu Rendering

The menu bar renders top-level labels (`File`, `Edit`, etc.) from the keys of
`self._menu`. On click, a small dropdown panel appears listing that menu's
`MenuAction` items. Items with `implemented=False` are rendered in `INK_4`
(dimmed) but are still clickable and call their handler (which is `_nyi`).
Items with `enabled=False` are rendered in `INK_4` and do **not** respond to clicks.

Implement hover highlight (`BG_3` background) on all menu labels and dropdown items.

This design means:
- No menu item is ever truly "decorative" — every item has a handler.
- Adding a real implementation later is a one-line change: replace `self._nyi`
  with the real method and set `implemented=True`.
- The chrome drawing code never needs to change when new menu items are added.

### Title Bar — height 44 px, below menu bar

Drawn as a filled rectangle (gradient `BG_2` → `BG_1`). Contains:

**Left side:**
- Traffic lights: three circles (12 px diameter, 8 px gap)
  - Red: `(255, 95, 87)` / Yellow: `(254, 188, 46)` / Green: `(40, 200, 64)`
- 1 px vertical divider, `LINE_DIM`
- Dungeon title text — `FONT_SERIF`, 15 px, `INK_1`

**Right side (from right, with gaps):**
- Status pill: rounded rect, `BG_0` fill, `LINE` border, `FONT_MONO` 11 px
  - Pulsing teal dot (7 px) + "Hearthfire · local"
- Mode switcher: two pills inside a rounded container
  - `◆ Design` — violet gradient when active
  - `◈ Play` — teal gradient when active
  - Inactive pill: transparent, `INK_3`

---

## Design Mode Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Menu Bar (26 px)                                                │
├─────────────────────────────────────────────────────────────────┤
│ Title Bar (44 px)                              [Design] [Play]  │
├───────────────┬─────────────────────────┬───────────────────────┤
│ Dungeon Tree  │   Design Chat           │   Inspector           │
│  240 px wide  │   flex (fills centre)   │   320 px wide         │
│               │                         │                       │
│  ▾ L1 · ...  │  [chat bubbles]         │ [Settings | Loops]    │
│    ▢ 1-A      │                         │                       │
│    ▢ 1-B      │                         │  Settings tab:        │
│  ▸ L2 · ...  │                         │  - Party size/level   │
│  ▸ L3 · ...  │                         │  - Theme, Levels      │
│               │  ──────────────────    │  - Complexity         │
│  ＋ Add level │  [chat input + Draft]   │  - Room inspector     │
│               │  [quick chips]          │  - Context docs       │
│               │                         │                       │
│               │                         │  Loops tab:           │
│               │                         │  - Level picker       │
│               │                         │  - Primary loop card  │
│               │                         │  - Sub-loops          │
│               │                         │  - Pattern library    │
├───────────────┴─────────────────────────┴───────────────────────┤
│ Inspector footer: [Test Drive]  [Start Play →]   (320 px wide)  │
└─────────────────────────────────────────────────────────────────┘
```

### Dungeon Tree Panel (left, 240 px)

Header: "DUNGEON" kicker label + "✓ validated" mono label (right-aligned).

Tree items:
- Level row: collapse arrow (▾/▸) + teal `◈` + "L{id} · {name}" — clickable to expand
- Room row (indented 26 px from left): path icon + room id + `·` + room name
  - Path A room: `▶` icon, teal text, 2 px teal left border
  - Path B room: `◇` icon, violet text, 2 px violet left border
  - Both paths: `◆` icon, indigo text (`oklch(0.75 0.12 260)`)
  - Neither: `▢` icon, `INK_3`
  - Selected: violet-tinted background
- Footer: `＋ Add level` row

### Design Chat Panel (centre, flex)

Header bar: "DESIGN CHAT" kicker + chip "Cycle: Lock & Key" (violet) + chip "model · local".

Chat area (scrollable):
- DM bubble: avatar circle (violet, `◆`), message in `BG_2` rounded rect, `FONT_SERIF` 13 px
- GM bubble: avatar circle (teal, `G`), message in teal-tinted rect, right-aligned, `FONT_UI` italic
- System divider: `sigil-hr` style — horizontal line with centred text

Input area (bottom, `BG_1` background):
- Quick chips above input: "Validate level" · "Add a secret door" · "Rebalance loot" · "Generate next level"
- Textarea (~3 rows), `FONT_UI` 13 px, placeholder text
- `Send` button (primary/teal)

**Quick chips — behavior:**
- Fixed set of 4 chips per mode (hardcoded; not user-configurable).
- **Design mode:** clicking a chip **pre-fills the input textarea** with the chip text — the GM can edit before pressing Send.
- **Play mode:** clicking a chip **sends immediately** to the DM agent — no pre-fill step.
- Design Mode chips: "Validate level" · "Add a secret door" · "Rebalance loot" · "Generate next level"
- Play Mode chips: "Describe room" · "Search for traps" · "Roll initiative" · "Listen at the door"

### Inspector Panel (right, 320 px)

Header: "INSPECTOR" kicker + tab buttons `Settings` / `Loops` (teal border/bg when active).

**Settings tab:**

*Party section* — `FONT_SERIF` 14 px heading "Party":
- Two-column grid: Size (number input) + Level (number input)

*Dungeon section* — "Dungeon" heading:
- Theme (text input)
- Levels (number input)
- Complexity (3-segment control: Light / Moderate / Deep)

*Room inspector* — appears when a room is selected:
- Room ID chip (violet) + type chip
- Room name in `FONT_SERIF` 18 px
- Dimensions in `FONT_MONO` 10 px
- Note text 12 px

*Context docs* — list of 4 document status rows (format: `✓ NNN words` when done, `○ pending` when not started, `○ N / N` when in progress):
- "Dungeon Setting Doc  ✓ 412 words"
- "Party Doc  ✓ 128 words"
- "Level Design Doc  ○ pending"
- "Room Design Doc  ○ 5 / 16"

**Loops tab:**

Level picker — 3 buttons (L1 / L2 / L3), teal-highlighted for active level.

Level name — `FONT_SERIF` 13 px.

Primary Loop card (if assigned):
- PRIMARY chip + pattern name (`FONT_SERIF` 14 px)
- Loop cycle diagram (SVG-equivalent drawn with Arcade arcs): entry ▶ teal arc to goal, violet dashed arc back
- Path A row: draggable room chips (teal border)
- Path B row: draggable room chips (violet border)
- Designer note in italic at bottom

Sub-loops (if any): same card style with SUB chip, × remove button.

Pattern Library (below sigil divider):
- Instruction: "Click to set as primary · shift-click to add as sub-loop"
- Grid of pattern cards: name + source chip + blurb + mini-cycle arc diagram
- Active pattern: teal border + teal name + "● ACTIVE" label

Inspector footer (pinned to bottom):
- `[Test Drive]` ghost button + `[Start Play →]` primary button

---

## Play Mode Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Menu Bar (26 px)                                                │
├─────────────────────────────────────────────────────────────────┤
│ Title Bar (44 px)                              [Design] [Play]  │
├──────────────────────────┬────────────────────────────┬─────────┤
│ Dungeon Chat             │  Dungeon Viewer (map)       │ Level   │
│  440 px wide             │  flex                       │ Stepper │
│                          │                             │ 70 px   │
│  Current Room banner     │  [Level name overlay]       │         │
│  ─────────────────────  │  [map canvas]               │  ▲      │
│  [chat bubbles]          │  [Legend overlay]           │  L1     │
│                          │  [Variant selector]         │  ──     │
│                          │  [Loop toggle strip]        │  L2     │
│  ─────────────────────  │                             │  L3     │
│  [quick chips]           │                             │  ▼      │
│  [chat input + Ask]      │                             │  N      │
└──────────────────────────┴────────────────────────────┴─────────┘
```

### Dungeon Chat Panel (left, 440 px)

Header bar: "DUNGEON CHAT" kicker + "Turn {n}" chip (teal) + room ID chip.

Current Room banner (below header, `BG_1` with violet gradient):
- "CURRENT ROOM" kicker (violet)
- Room name `FONT_SERIF` 19 px
- Room note 12 px `INK_3`

Chat area (scrollable, `ref` scrolls to bottom on new message):
- GM bubble: label "GM", dashed border, italic, `INK_3`
- DM bubble: label "◆ Dungeon", `BG_2` fill, `FONT_SERIF` body
- System: sigil-hr divider

Quick chips above input: "Describe room" · "Search for traps" · "Roll initiative" · "Listen at the door"
(Clicking a chip sends the message immediately — no pre-fill step in Play mode.)

Input area: textarea (~3 rows) + `Ask` button.

### Map Panel (centre, flex)

Header: "DUNGEON VIEWER" kicker + "◇ Sundered Crown" gold chip + Jump-to-room select.

Map canvas (fills available space, 18 px padding):
- Rounded border `LINE`, `BG_0` background
- Map rendered by active `MapRenderer` (grid / tiles / graph)
- Loop overlay on top if `active_loop_id` is set

Overlays (positioned absolutely within the canvas):
- Top-left: Level number (teal, `FONT_MONO`) + Level name (`FONT_SERIF` 22 px) + grid dimensions
- Bottom-left: legend (party ● / shrine ▢ / boss ▢ / vault ▢ / unseen ▢)
- Top-right: variant selector (Grid / Tiles / Graph) — borderless mini toggle
- Bottom-right: Loops toggle strip (visible if level has loops)

### Level Stepper Rail (right, 70 px)

Centred column layout, `BG_1` background, left border `LINE`:
- ▲ button (up one level)
- "L{id}" label (teal, `FONT_MONO`)
- ▼ button (down one level)
- Vertical gradient divider
- Level buttons — one square button per level (L1 / L2 / L3…) — teal border + glow when active
  - **≤5 levels:** static column, all buttons visible at once
  - **>5 levels:** scrollable sub-column within the rail; ▲/▼ navigation buttons
    scroll by one level; the active level button is always scrolled into view
- Stretch spacer
- Compass rose circle (36 px, "N" in `FONT_SERIF`)

---

## Map Renderers

All three renderers receive a `region: tuple[float, float, float, float]`
(left, bottom, width, height in Arcade screen coordinates) and the current
`Level` data object.

### Grid Renderer

Graph-paper style:
- Dark background (`BG_0`)
- Minor grid lines every cell (0.5 px, `LINE_DIM` at 35% opacity)
- Major grid lines every 5 cells (0.6 px, slightly brighter)
- Rooms: filled rect (colour by type) + outline (1–2 px, colour by type)
- Current room: teal 2 px border + teal drop-shadow effect
- Room number: centred in room, `FONT_SERIF`
- Connections: lines between room centres (3–6 px), dashed for `hole` type
- Entry markers: teal-filled circle with ▼ label

### Tiles Renderer

Shaded top-down cell view:
- Black background
- Cell-by-cell alternating shading for texture
- Edge bevels (1 px highlight on top/left edges)
- Room outlines coloured by type
- Current room: animated pulsing circle overlay (opacity animation)
- Connections: soft teal glowing lines on top

### Graph Renderer

Abstract node graph:
- `BG_0` background with subtle dot grid (0.8 px dots every 22 px)
- Rooms as circles (26 px radius), positioned by room centre coordinates
- Edges as lines with centred type labels in small rounded rects
- Node fill by type, outline by type + current room teal glow
- Node number (`FONT_SERIF` 18 px) + type label below

### Loop Overlay

Drawn after the map renderer:
- Path A: 3 px teal line through room centres (with glow blur effect approximation)
- Path B: 3 px violet dashed line (6 px dash, 4 px gap)
- Entry marker: teal circle (r=10) + "ENTRY" label above
- Goal marker: violet circle (r=10) + "GOAL" label above

---

## Interaction Behaviours

| Action | Result |
|---|---|
| Click room on map | Select room, add to visited, DM narrates entry |
| Click room in dungeon tree | Select room in tree, highlight in map |
| Click level button in stepper | Jump to level, DM narrates arrival |
| Click loop in loops toggle strip | Toggle loop overlay on/off |
| Click pattern card in library | Set as primary loop, auto-assign rooms |
| Shift-click pattern card | Add as sub-loop |
| Drag room chip in path editor | Reorder rooms within path A or B |
| Press Enter in play chat | Send message (shift+Enter for newline) |
| Press Ctrl+Enter in design chat | Send message |
| Click mode switcher | Switch Design ↔ Play, preserve dungeon state |

---

## Room Selection Contract

When a room is selected (via tree click or map click), all of the following
state changes occur atomically:

1. `selected_room_id` is updated in the active view's state
2. The dungeon tree highlights the room row (violet background)
3. The map highlights the room (teal border + glow — Play Mode only)
4. The Inspector panel (Settings tab) updates the Room Inspector card with the
   selected room's id, type, dimensions, and note
5. In Play Mode: room click also updates `current_room_id`, adds to `visited`,
   and triggers the DM narration flow

Tree click and map click both call the same `on_select_room(room_id)` handler
on the active view. They are not separate code paths.

---

## Typing Indicator

While the LLM is responding, a typing indicator appears as the last item in the
chat scroll area. It replaces the DM bubble that will eventually arrive.

Visual: a DM-style bubble (same background and border as a DM bubble) containing
three animated dots that cycle through states:

```
◆  ·  ·         (frame 1)
◆  ■  ·         (frame 2)
◆  ■  ■         (frame 3)
◆  ·  ·         (repeat)
```

- Color: `VIOLET` dots on `BG_2` background
- Animation: cycle frames every 500 ms (checked in `on_update`)
- Label: "◆ Dungeon" in `FONT_MONO` `TEXT_XS` (same as DM bubble header)
- The Send button and input textarea are **disabled** (greyed out) while the
  indicator is visible

When the LLM result arrives, the indicator is removed and the real DM bubble
is appended in its place.

---

## Chat Scroll Behaviour

**Auto-scroll rule:** The chat panel scrolls to the bottom whenever a new message
is appended, **unless** the user has manually scrolled up.

Scroll-lock detection:
- Track `user_has_scrolled_up: bool` on the chat panel
- Set `True` when the user scrolls upward (scroll position is not at the bottom)
- Set `False` when the user manually scrolls back to the bottom
- When `user_has_scrolled_up` is `False`, auto-scroll on every new message
- When `True`, append messages silently without changing scroll position
- A small "↓ New message" badge appears at the bottom-right of the chat area
  when a message arrives while scrolled up. Clicking it scrolls to bottom and
  clears the badge.

---

## Mode Switch — State Preservation

When switching between Design and Play mode, the following state is preserved:

| State | Preserved |
|---|---|
| Loaded `Dungeon` object | Yes — the same object reference is passed to both views |
| `selected_room_id` | Yes — selection carries across modes |
| `active_loop_id` | Yes — active loop carries across modes |
| `map_variant` | Yes — owned by `AppConfig`, shared |
| `current_room_id` (Play) | Yes |
| `visited_rooms` (Play) | Yes |
| Chat scroll position | No — resets to bottom on mode switch |
| Chat transcript content | Yes — stored in `SessionState`, not the view |
| `loops_by_level` (Design) | Yes — owned by `DesignView`, not rebuilt on switch |
| Typing indicator | No — cleared on mode switch; any pending LLM call is abandoned |

On mode switch, call `thread.join(timeout=0.1)` on any active LLM thread and
discard the result rather than waiting for it.

---

## Error States

### LLM Unavailable (no API key)

At startup, if `ANTHROPIC_API_KEY` is not set:
- Both chat panels show a pinned system message at the top:
  `"⚠ AI features disabled — ANTHROPIC_API_KEY not set"`
- The Send button and input textarea are disabled
- All other UI (map, tree, inspector) is fully functional

### LLM Call Failed

If an LLM call returns an error (rate limit, network, auth):
- A system bubble appears in the chat:
  `"⚠ The dungeon is silent. (Rate limit exceeded — try again in a moment.)"`
- The typing indicator is removed
- The Send button re-enables immediately — the user can retry
- No dialog, no crash

### File Save/Load Failed

If `DungeonRepository.save()` raises an `OSError`:
- A system bubble appears in the design chat:
  `"⚠ Save failed. ({error message})"`
- The dungeon state in memory is unchanged

### Dungeon File Corrupt

If `Dungeon.model_validate()` raises a `ValidationError` on load:
- A system bubble appears:
  `"⚠ Could not load dungeon — file may be corrupt or from a newer version."`
- The sample dungeon is loaded as a fallback

---

## Loop Overlay Label Positioning

Entry and goal labels for the loop overlay are drawn relative to the room centre
point. Use the following rules to keep labels inside the canvas bounds:

```
Default position: 16 px ABOVE the room centre (anchor: bottom-centre of text)

Edge clipping overrides (applied in order, first match wins):
  - Room centre y > canvas_height * 0.90  →  draw BELOW instead (+16 px)
  - Room centre x < canvas_width  * 0.10  →  draw to the RIGHT (+16 px, same y)
  - Room centre x > canvas_width  * 0.90  →  draw to the LEFT  (-label_width - 16 px)
  - Room centre y < canvas_height * 0.10  →  draw ABOVE (default, no override)
```

Labels use `FONT_MONO`, `TEXT_XS` (9 px), uppercase, colour matching their path
(`TEAL` for entry, `VIOLET` for goal).

Only one loop overlay is shown at a time. The active loop is set by
`active_loop_id` on the view. Multiple overlays are not supported.
