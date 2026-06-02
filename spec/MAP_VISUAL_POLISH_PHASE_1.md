# Dungeon Daddy — Graph Map Background + Room Frame Asset Instructions v2

## Goal

Add asset-backed visual polish to the **Play Mode Graph map** without changing layout behavior.

This task adds:

1. A static pixel-art atmospheric background PNG behind the Graph map viewport.
2. Transparent occult-silver PNG room frames over Graph mode room nodes.

The image assets are generated separately by the user. Claude Code should only add the code support and look for the files at the exact paths listed below.

---

## Current Repo Context

The latest implementation has moved Graph rendering further into the layout pipeline. Graph mode is still rendered through:

```text
MapPanel -> LayoutRenderer -> LayoutResult rooms/edges
```

The primary files are:

```text
dungeon_daddy/ui/panels/map_panel.py
dungeon_daddy/map/layout_renderer.py
dungeon_daddy/map/dungeon_layout/seed_layout.py
dungeon_daddy/ui/theme.py
```

Important current behavior:

- `MapPanel.draw()` still owns the map viewport, scissor clipping, and the Graph renderer call.
- `LayoutRenderer.draw()` now accepts extra Graph presentation arguments:

```python
level: Level | None = None
presentation_config: GraphPresentationConfig | None = None
panel_x: float = 20.0
panel_y: float = 20.0
canvas_w: float = 1200.0
canvas_h: float = 800.0
viewport_x: float = 0.0
viewport_y: float = 0.0
```

- `LayoutRenderer.draw()` currently calls `_draw_atmosphere(...)` when `presentation_config` is provided.
- Do **not** remove or break the existing Graph atmosphere, detail panel, room hover, room selection, connection markers, dashed connection rendering, or panel-placement behavior.

---

## Graph Room Dimensions

Graph mode room rectangles are still defined in layout space in:

```text
dungeon_daddy/map/dungeon_layout/seed_layout.py
```

Current constants:

```python
ROOM_W = 120.0
ROOM_H = 80.0
ROOM_GAP = 60.0
```

`LayoutRenderer` scales rooms by the current Graph zoom:

```python
ww = rect.w * zoom
wh = rect.h * zoom
```

So room frame assets should be treated as **base layout-size assets** and drawn at:

```python
frame_width = 136 * zoom
frame_height = 96 * zoom
```

---

## Required Asset Paths and Names

Claude Code should look for assets at these exact repo paths.

### Background image

```text
dungeon_daddy/assets/ui/map/background_graph_default.png
```

Expected dimensions:

```text
1780 x 1584 px
```

Default display target at the standard 1400x900 app window:

```text
890 x 792 px
```

Reasoning:

- Default window: `1400 x 900`
- Play chat panel: `440 px`
- Stepper rail: `70 px`
- Top chrome: `70 px`
- Map panel header: `38 px`
- Graph map viewport at default size: `890 x 792 px`
- The source image is 2x the default viewport for better scaling quality.

### Room frame images

```text
dungeon_daddy/assets/ui/map/room_frames/frame_default.png
dungeon_daddy/assets/ui/map/room_frames/frame_current.png
dungeon_daddy/assets/ui/map/room_frames/frame_hover.png
dungeon_daddy/assets/ui/map/room_frames/frame_locked.png
dungeon_daddy/assets/ui/map/room_frames/frame_memory.png
dungeon_daddy/assets/ui/map/room_frames/frame_danger.png
```

Expected dimensions for all frame PNGs:

```text
136 x 96 px
```

Reasoning:

- Graph room logical size is `120 x 80`.
- Frame asset is `136 x 96`, giving an 8 px decorative overhang on each side.
- The clickable/hit-test area should remain the existing `120 x 80` room rectangle.
- Draw the frame centered over the room rectangle.

---

## Implementation Requirement 1 — Background Image

### Where to implement

Prefer implementing background texture loading and drawing in:

```text
dungeon_daddy/ui/panels/map_panel.py
```

Reason: `MapPanel` already knows the exact viewport rectangle:

```python
map_w = w - PANEL_STEPPER_WIDTH
map_h = h - _HEADER_H
ctx.scissor = (int(x), int(y), int(map_w), int(map_h))
```

### Draw order

Inside the existing scissor-clipped map content area, draw in this order:

1. Solid fallback map background color.
2. `background_graph_default.png`, if present and active variant is `Graph`.
3. Existing `LayoutRenderer.draw(...)` call.
4. Existing overlays outside/after the scissor block.

The current `LayoutRenderer._draw_atmosphere(...)` should remain in place. It should render **over** the image background and under rooms/edges, preserving the newer atmospheric vignette/frame behavior.

### Drawing target

Draw the background centered at:

```python
x + map_w / 2
 y + map_h / 2
```

With size:

```python
map_w by map_h
```

Do not let the background cover:

- Chat panel
- Header bar
- Stepper rail
- Menu/title chrome
- Loop chips
- Detail panel

### Missing file behavior

If `background_graph_default.png` is missing:

- Do not crash.
- Keep the current solid `BG_0` fallback.
- Log a warning once, not every frame.

---

## Implementation Requirement 2 — Room Frame Textures

### Where to implement

Implement room frame texture loading and drawing in:

```text
dungeon_daddy/map/layout_renderer.py
```

Reason: `LayoutRenderer._draw_rooms(...)` owns Graph room rectangle rendering and already has access to:

```python
rect.room_id
style
view_state
selected_room_id
zoom
wx, wy, ww, wh
```

### Current room rendering location

In `_draw_rooms(...)`, the current code draws:

```python
arcade.draw_rect_filled(xywh, fill)
arcade.draw_rect_outline(xywh, border, style.border_width)
```

Then it applies glow/second outline/critical path/selected outline and label text.

### New desired room render order

For each room, render in this order:

1. Existing room fill rectangle.
2. Existing room outline / glow / second outline / critical path outline.
3. Frame PNG overlay centered over the room.
4. Text label.
5. Role marker / badge text.

The label should remain readable. If the frame's label band makes centered text awkward, keep the label centered for this pass rather than changing layout behavior.

### Frame placement

Given current values:

```python
wx = self._wx(rect.x, origin_x, zoom)
wy = self._wy(rect.y, origin_y, zoom)
ww = rect.w * zoom
wh = rect.h * zoom
center_x = wx + ww / 2
center_y = wy + wh / 2
```

Draw frame at:

```python
frame_width = 136 * zoom
frame_height = 96 * zoom
```

Centered at:

```python
center_x, center_y
```

Do **not** change `rect.w`, `rect.h`, hit testing, layout bounds, camera fit, or connection routing.

---

## Frame Selection Rules

Use frame textures in this priority order:

```text
current/selected > hover > memory/danger/locked > default
```

### `frame_current.png`

Use when the room is visually selected/current.

Treat a room as selected/current if:

```python
rect.room_id == selected_room_id
```

or, when `view_state` is available:

```python
rect.room_id == view_state.selected_room_id
```

### `frame_hover.png`

Use when:

```python
rect.room_id == view_state.hovered_room_id
```

Selected/current should win over hover.

### `frame_memory.png`

Load and support the asset, but do not invent memory state yet. Add a helper hook/stub only if useful.

### `frame_danger.png`

Load and support the asset, but do not invent danger state yet. Add a helper hook/stub only if useful.

### `frame_locked.png`

Load and support the asset, but do not invent locked state yet. Add a helper hook/stub only if useful.

### `frame_default.png`

Use for all normal rooms.

---

## Asset Loading Requirements

Add a small safe asset-loading helper rather than calling `arcade.load_texture()` inside the draw loop.

Acceptable approaches:

1. Add lazy-loaded fields to `MapPanel` for the background texture.
2. Add lazy-loaded fields to `LayoutRenderer` for frame textures.
3. Or create a small reusable helper class such as `MapArtAssets`.

Requirements:

- Load textures once per object/process lifecycle.
- Missing assets must not crash the app.
- Missing assets should log a warning once.
- Rendering should gracefully fall back to the existing primitive rectangles.
- Use robust path resolution based on the package location, not current working directory.

Suggested asset root resolution:

```python
from pathlib import Path
ASSET_ROOT = Path(__file__).resolve().parents[... ] / "assets" / "ui" / "map"
```

Be careful: `map_panel.py` and `layout_renderer.py` live at different package depths, so calculate parents accordingly.

Expected asset root:

```text
dungeon_daddy/assets/ui/map/
```

Expected frame directory:

```text
dungeon_daddy/assets/ui/map/room_frames/
```

---

## Preserve Current New Graph Features

The latest code now includes enhanced Graph presentation behavior. Do not regress it.

Preserve:

- `GraphPresentationConfig`
- `_draw_atmosphere(...)`
- `build_atmosphere_spec(...)`
- detail panel rendering
- `build_room_detail(...)`
- `format_detail_panel(...)`
- panel placement via `compute_panel_position(...)`
- connection marker glyphs
- dashed connection rendering
- hover connection emphasis
- selected-room connected-room fading behavior
- long linear floor fit padding

This asset task should layer on top of the current system.

---

## Do Not Change

Do not change:

- Graph layout algorithm
- `ROOM_W`, `ROOM_H`, or `ROOM_GAP`
- room hit testing
- connection routing
- camera fit logic except if absolutely needed for visual asset clipping
- map JSON schema
- memory system behavior
- generated scene-card behavior
- Grid mode
- Tiles mode

---

## Testing / Verification Checklist

### Manual visual checks

1. Run Dungeon Daddy.
2. Open Play Mode.
3. Switch map to Graph mode.
4. Confirm background image fills the Graph viewport.
5. Confirm background does not cover chat panel, header, stepper rail, loop chips, or detail panel.
6. Confirm all room nodes have frame overlays.
7. Hover a room and confirm `frame_hover.png` appears.
8. Select a room and confirm `frame_current.png` appears.
9. Confirm selected/current frame wins over hover.
10. Zoom in/out from 0.5 to 3.0 and confirm frames remain centered.
11. Pan and confirm frames move with rooms.
12. Click room nodes and confirm hit testing still uses the original room rectangle.
13. Remove or rename one PNG and confirm the app does not crash.

### Regression checks

- Grid mode still renders.
- Tiles mode still renders.
- Graph mode pan works.
- Graph mode zoom works.
- Graph mode fit-to-layout works.
- Room selection still triggers Play Mode room entry.
- Connection selection still works.
- Existing tests pass.

---

## Acceptance Criteria

### Background

- `dungeon_daddy/assets/ui/map/background_graph_default.png` is loaded once when present.
- The background is drawn only in Graph mode.
- It fills the map viewport beneath the Graph content and existing atmosphere overlay.
- It scales when the window is resized.
- Missing file falls back to existing `BG_0` behavior without crashing.

### Room frames

- Frame files are loaded once when present.
- Graph rooms display a centered 136x96 frame overlay scaled by Graph zoom.
- Existing room rectangles remain 120x80 in layout space.
- Default rooms use `frame_default.png`.
- Hovered rooms use `frame_hover.png`, unless selected/current.
- Selected/current rooms use `frame_current.png`.
- Missing frame assets do not crash the app.
- Hit testing, camera fitting, routing, detail panel placement, and selection behavior remain unchanged.

---

## Optional Future Hooks Only

Structure the implementation so these can be added later, but do not fully implement unless trivial and low-risk:

1. Room thumbnail/image area inside the frame.
2. `frame_memory.png` activated by room-level memory state.
3. `frame_danger.png` activated by danger/instability state.
4. `frame_locked.png` activated by locked/unvisited state.
5. Pixel-art chain or track connectors replacing primitive lines.

---

## Final Instruction

This is a visual skin layer over the current Graph map.

The current screenshots show that Graph mode has improved presentation, detail panels, markers, and selection behavior. Preserve all of that. The background and frames should enhance the existing system, not replace it.
