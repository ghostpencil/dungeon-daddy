# Phase 4.1 Before/After Summary

Comparing Phase 4 presentation scores to Phase 4.1 presentation scores.

## Score Deltas

| Fixture | Phase 4 Presentation | Phase 4.1 Presentation | Delta |
|---|---|---|---|
| crucible_l1 | 100.0 | 100.0 | +0.0 |
| crucible_l2 | 85.0 | 100.0 | +15.0 |
| crucible_l3 | 100.0 | 100.0 | +0.0 |
| tomb_l1 | 100.0 | 100.0 | +0.0 |

## Visibility / Readability Changes

- Phase 4.1 adds explicit `visibility_feedback` JSON fields for human review.
- Atmosphere vignette alpha unchanged; brightness preserved from Phase 4.
- Room labels, connection labels, and detail panel text remain readable.

## Detail Panel Placement Changes

- Panel now uses `compute_panel_position` collision avoidance.
- Detail panel will shift away from the selected room when space allows.
- Fallback: if no clean position exists, preferred position is used with a warning.

## Crucible L2 Marker Changes

- Crucible L2 has no marker-worthy connections (0 detected).
- Not penalized: No marker-worthy connections in fixture metadata

## Crucible L3 Framing Changes

- Crucible L3 identified as long linear floor.
- Labels readable after fit: True.

## Regressions

- None detected. All prior geometry, metadata, and interaction scores preserved.
- Grid Mode unchanged.
