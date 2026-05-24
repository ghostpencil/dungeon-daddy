## Dungeon Map Zoom Feature

Add zoom support to the dungeon map view.

### Goal

The user should be able to zoom the dungeon map in and out while keeping the map readable, centered, and easy to navigate.

### Required Behavior

- Support zooming in and out of the dungeon map.
- The zoom should affect only the map view, not the rest of the UI.
- Map tiles, room shapes, corridors, grid lines, and tokens should scale together.
- The current pan/scroll position should be preserved as much as possible when zooming.
- Zooming should feel smooth and predictable.
- The map should not become unusably tiny or excessively large.

### Controls

- Mouse wheel zooms in and out when the cursor is over the map.
- Optional keyboard controls:
    - `+` zooms in
    - `-` zooms out
    - `0` resets zoom to default

### Zoom Limits

- Minimum zoom: `0.5x`
- Default zoom: `1.0x`
- Maximum zoom: `3.0x`

### Implementation Notes

- Introduce a `zoom_level` value in the map view state.
- Apply zoom as a transform during rendering rather than modifying the underlying dungeon/map data.
- Keep dungeon coordinates separate from screen coordinates.
- Add helper methods for converting between:
    - map coordinates
    - world coordinates
    - screen coordinates
- Do not change the dungeon generation, dungeon data model, or saved map format.

### Acceptance Criteria

- The user can zoom in and out of the dungeon map.
- At `1.0x`, the map renders exactly as it does today.
- Zooming does not distort rooms, corridors, tokens, or grid alignment.
- Panning still works correctly at different zoom levels.
- Reset zoom returns the map to `1.0x`.
- Existing map rendering tests continue to pass.
- Add or update tests for zoom level changes and coordinate conversion.