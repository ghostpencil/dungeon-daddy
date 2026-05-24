## Status: COMPLETED

---

## Goal

Improve the map view usability in the Dungeon Daddy Arcade UI by:

Making the right-side vertical arrow/navigation panel fully opaque so the map is not visible underneath it.
---

## Problem: Right Arrow Panel Transparency

### Current Behavior

When the Arcade window is resized, the right-side panel containing the up/down arrow buttons overlaps the map area. The map remains visible underneath the panel.

### Desired Behavior

The right-side arrow panel should visually cover the map area completely.

### Requirements

- The right-side arrow panel must have an opaque background.
- The background color should match the existing dark UI panel styling.
- The map, room boxes, connector lines, and grid should not be visible beneath the arrow panel.
- This should remain true after resizing the Arcade window.
- The up and down arrow buttons should remain visible and clickable.
- The level indicator text, such as `L2`, should remain visible and readable.

### Acceptance Criteria

- Resize the window wider and narrower.
- The right-side arrow panel always appears as a solid UI panel.
- No map elements are visible behind the arrow panel.
- Arrow buttons still work after resizing.
