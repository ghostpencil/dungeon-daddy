# Phase 2.5 → Phase 3 Before/After Comparison

| Fixture | Geom 2.5→3 | Sem 2.5→3 | Meta 2.5→3 | Interaction Score | Notes |
|---|---|---|---|---|---|
| crucible_l1 | 100.0 (Δ+0.0) | 78.0 (Δ+0.0) | 100.0 (Δ+0.0) | 100.0 | — |
| crucible_l2 | 100.0 (Δ+0.0) | 82.2 (Δ+0.0) | 100.0 (Δ+0.0) | 100.0 | — |
| crucible_l3 | 100.0 (Δ+0.0) | 82.8 (Δ+0.0) | 100.0 (Δ+0.0) | 100.0 | — |
| tomb_l1 | 100.0 (Δ+0.0) | 81.0 (Δ+0.0) | 100.0 (Δ+0.0) | 100.0 | — |

## New Interaction Features (Phase 3)

- Room hover: border brightens/thickens on mouse-over
- Room selection: focus mode — connected rooms highlight, unrelated fade
- Critical path emphasis: stronger when a critical-path room is selected
- Connection hover: brightens near segment
- Room detail panel: data assembled for selected room (name, role, connections, notes)
- Keyboard controls: R = recenter, Escape = clear selection
- GraphViewState: camera, hover, selection kept separate from stable LayoutResult

## Known Limitations

- Detail panel is data-only; not yet rendered visually inside the Arcade window
  (panel data available via `build_room_detail`; visual rendering is Phase 4 scope)
- Grid Mode intentionally unchanged
