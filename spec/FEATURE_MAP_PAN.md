# Feature: Map View Overlay Fix and Pan Tool

**Status: COMPLETE — all MUP tests passed 2026-04-29**

## Goal

Improve the map view usability in the Dungeon Daddy Arcade UI by:

1. Adding a dedicated map panning tool so the GM can move around the map without accidentally selecting rooms.

---

## Problem : Add Map Panning Tool

### Current Behavior

Clicking inside the map area is primarily used to interact with rooms. There is no dedicated way to pan the map view.

### Desired Behavior

Add a dedicated pan/hand tool that allows the GM to drag the map view without selecting or activating rooms.

---

## Pan Tool Requirements

### Tool Selection

- Add a new map interaction tool called `Pan` or `Hand`.
- The tool should be accessible from the map toolbar near the existing `Grid`, `Tiles`, and `Graph` buttons, or another clear map-control area.
- The selected tool should be visually highlighted.
- Only one map interaction tool should be active at a time.

### Pan Behavior

When the Pan tool is active:

- Left mouse drag inside the map viewport should pan the map.
- Dragging should move the visible map content in the direction of the mouse drag.
- Clicking or dragging on rooms should not select, enter, activate, or edit rooms.
- Releasing the mouse button should stop panning.
- Panning should feel smooth and immediate.
- The cursor should ideally show a hand or grab-style cursor while the tool is active, if Arcade supports this cleanly.

### Non-Pan Behavior

When the Pan tool is not active:

- Existing room clicking behavior should remain unchanged.
- Clicking a room should still perform the current room interaction.
- Existing map view modes such as `Grid`, `Tiles`, and `Graph` should continue to work as they do now.

---

## State Requirements

Add map view offset state if it does not already exist.

Example:

```python
map_offset_x: float
map_offset_y: float
is_panning: bool
last_mouse_x: float
last_mouse_y: float
active_map_tool: Literal["select", "pan"]
```

---

## Execution Plan

### Status: COMPLETE

Build order — tests written before each implementation step.

---

### Step 1 — Unit tests (TDD red phase) ← DONE
File: `tests/unit/map/test_map_pan.py`

Tests (no arcade display needed — no `setup()` call, no draw patches required):
- `test_select_tool_press_returns_false` — handle_mouse_press returns False in select mode
- `test_pan_tool_press_returns_true` — handle_mouse_press returns True in pan mode
- `test_drag_accumulates_offset_while_panning` — dx/dy accumulate into pan_offset
- `test_drag_no_effect_when_not_panning` — offset unchanged if _is_panning is False
- `test_release_stops_panning` — _is_panning becomes False after release

---

### Step 2 — Pan state + interaction methods on MapPanel ← DONE
File: `dungeon_daddy/ui/panels/map_panel.py`

Add to `__init__`:
```python
self._active_tool: str = "select"   # "select" | "pan"
self._pan_offset_x: float = 0.0
self._pan_offset_y: float = 0.0
self._is_panning: bool = False
```

Add properties: `pan_offset -> tuple[float, float]`, `active_tool -> str`

Add methods:
- `handle_mouse_press(x, y, button) -> bool` — starts panning if pan tool active, returns True; else False
- `handle_mouse_drag(x, y, dx, dy, button)` — accumulates offset when panning
- `handle_mouse_release(x, y, button)` — clears `_is_panning`

---

### Step 3 — Pan button in tab bar ← DONE
File: `dungeon_daddy/ui/panels/map_panel.py`

Add `"Pan"` button to `_setup_tabs`, visually separated from Grid/Tiles/Graph variant tabs
(e.g. extra left margin gap). Clicking a variant tab sets `_active_tool = "select"`;
clicking Pan sets `_active_tool = "pan"` and highlights accordingly.
`_active_variant` and `_active_tool` are independent — pan does not change the view mode.

---

### Step 4 — Apply pan offset in draw() ← DONE
File: `dungeon_daddy/ui/panels/map_panel.py`

Change renderer/overlay call site:
```python
origin_x = x + PAD_MD + self._pan_offset_x
origin_y = y + PAD_MD + self._pan_offset_y
```

---

### Step 5 — Wire mouse events in PlayView ← DONE
File: `dungeon_daddy/views/play_view.py`

`on_mouse_press`:
- Delegate to `self._map.handle_mouse_press(x, y, button)` before hit-testing
- If it returns True (pan consumed), return early
- Otherwise apply `self._map.pan_offset` to origin before cell-coord calculation

Add:
```python
def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
    self._map.handle_mouse_drag(x, y, dx, dy, buttons)

def on_mouse_release(self, x, y, button, modifiers):
    self._map.handle_mouse_release(x, y, button)
```

---

### Future / out of scope
- Min/max pan bounds
- Reset pan button

---

## Manual UI Tests

Run the app: `python -m dungeon_daddy`
Load the sample dungeon, switch to Play mode.

---

**MUP-1 — Pan button appears in tab bar**
Expected: tab bar shows [Grid] [Tiles] [Graph]  [Pan] with a visual gap before Pan.
Status: PASSED

---

**MUP-2 — Pan button highlights when active**
1. Click [Pan]
Expected: Pan button highlighted (teal border/bg); Grid/Tiles/Graph buttons go inactive.
Status: PASSED

---

**MUP-3 — Switching back to Grid deactivates Pan**
1. Click [Pan], then click [Grid]
Expected: Grid is highlighted; Pan is inactive.
Status: PASSED

---

**MUP-4 — Pan tool moves the map**
1. Click [Pan]
2. Click and drag inside the map area
Expected: map content moves smoothly in the drag direction; no room is selected or highlighted.
Status: PASSED

---

**MUP-5 — Map content clipped to viewport**
1. Click [Pan], drag the map far left or far down
Expected: room rectangles and connector lines are clipped at the map viewport edge; no content bleeds into the chat panel, stepper rail, or tab bar.
Status: PASSED

---

**MUP-6 — Pan drag outside viewport has no effect**
1. Click [Pan]
2. Click and drag starting from the chat panel (left of map area)
Expected: map does not move; no panning begins.
Status: PASSED

---

**MUP-7 — Select tool still works after panning**
1. Pan the map so a room is visible at a new position
2. Click [Grid] to return to select tool
3. Click on a visible room
Expected: room is highlighted with teal stroke; chat logs "You enter [room name]."
Status: PASSED

---

**MUP-8 — Room click hit-test respects pan offset**
1. Pan the map so a room moves significantly from its original position
2. Click [Grid], then click the room at its *new* visual position
Expected: correct room is selected (not the room that was originally at that screen position).
Status: PASSED