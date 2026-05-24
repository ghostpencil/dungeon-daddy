# Feature Refinement: Localized Connection Routing and Route Scoring Improvements

## Feature Name

Localized Dungeon Connection Routing Refinement

## Background

The initial obstacle-aware routing implementation successfully avoids drawing connection lines directly through unrelated rooms.

However, some generated routes now take excessively large detours around the map. While technically valid, these routes reduce readability and visually dominate the dungeon layout.

Example issue:

```text
A connection between two nearby rooms routes around half the map perimeter instead of taking a smaller local detour.
```

The renderer now needs better heuristics and candidate generation so routed paths remain visually reasonable and localized.

---

# Root Cause Analysis

## Why pure scoring changes are insufficient

The original draft of this spec proposed raising the intersection penalty from `10000` to `100000`. This would make the problem worse, not better.

The perimeter loop occurs when all four local detour candidates cross other rooms, but a long clean route around the map perimeter does not. In that case:

```text
perimeter_score = 0 * 100000 + large_length_penalty
local_score     = 1 * 100000 + small_length_penalty
```

`0 * 100000` always beats `1 * 100000` regardless of how large the length/locality penalties are. Raising the intersection multiplier makes a clean perimeter route even harder to beat.

**Scoring improvements alone only help when comparing paths with equal intersection counts.**

## The two structural bugs

### Bug 1 — Waypoints are unclamped

The four detour candidates use the raw blocker edge coordinates:

```python
[from_port, (fx, bt + m), (tx, bt + m), to_port]   # top bypass
```

`bt + m` can place the waypoint far outside the local area. There is no check that the intermediate waypoint stays near the two rooms. If all four local candidates also cross other rooms, the candidate with the fewest total intersections wins — and that might be a path that overshoots by 30+ grid units.

### Bug 2 — Left/right candidates degenerate when ports are horizontally aligned

When `fy == ty` (both ports at the same vertical position), the left and right candidates collapse:

```python
[from_port, (bl - m, fy), (bl - m, ty), to_port]
# fy == ty → middle two points are identical → straight horizontal line
# This straight line still passes through the original blocker
```

These degenerate candidates score as if they avoid the blocker but they do not.

---

# Goal

Improve routed dungeon connections so they:

- Prefer short local detours
- Avoid huge perimeter loops
- Remain visually readable
- Preserve the overall dungeon shape
- Avoid visually dominating the room layout
- Feel appropriate for a dungeon map

The routing system should prioritize:

```text
Readable > Perfect
```

A slightly imperfect local route is often preferable to a mathematically clean but absurdly large detour.

---

# Design Principle

Dungeon connection routing should feel:

- Compact
- Intentional
- Localized
- Human-readable

The renderer should strongly prefer routes that stay near the connected rooms.

---

# Functional Requirements

## 1. Clamp Detour Waypoints to Local Bounds (Primary Fix)

For every connection, calculate a local routing region:

```python
local_bounds = bounding_rect(source_room, target_room) expanded by ROUTE_BOUNDING_MARGIN
```

In `route_detour`, clamp each candidate waypoint so it does not exceed the local bounds:

```python
bypass_top    = min(bt + m, local_top)
bypass_bottom = max(bb - m, local_bottom)
bypass_left   = max(bl - m, local_left)
bypass_right  = min(br + m, local_right)
```

If clamping causes a candidate waypoint to land inside the blocker (the blocker extends past
the local boundary), that candidate will intersect the blocker and score accordingly. This is
correct — no route that stays local can cleanly avoid this blocker, so the least-bad local
path should be chosen rather than escaping the map.

```python
ROUTE_BOUNDING_MARGIN = 4   # grid units — approximately 2× typical room width
```

### Acceptance Criteria

- Every routed connection calculates a local routing region.
- Detour waypoints are clamped to that region before candidates are evaluated.
- No detour candidate can place a waypoint outside the local bounds.
- When the blocker extends past the local bounds, the algorithm accepts a slightly
  intersecting local path rather than routing around the whole map.

---

## 2. Fix Left/Right Candidate Degeneration

When `fy == ty` (ports are horizontally aligned), the left and right detour candidates
must use an offset so the intermediate waypoint is not colinear with the start and end points.

If `fy == ty`, replace the left/right candidates with orthogonal detour shapes that
include a vertical step so the path genuinely bypasses the blocker:

```python
# When fy == ty: step above/below the blocker, traverse left/right, step back
DEGENERATE_Y_OFFSET = ROUTE_BOUNDING_MARGIN / 2
mid_y = fy + DEGENERATE_Y_OFFSET   # use - DEGENERATE_Y_OFFSET for the other variant

left_candidate  = [from_port, (fx, mid_y), (bl - m, mid_y), to_port]
right_candidate = [from_port, (br + m, mid_y), (tx, mid_y), to_port]
```

> **Note**: The last segment of each candidate `(bl - m, mid_y) → to_port` is
> diagonal when `mid_y ≠ ty`. `line_intersects_rect` handles diagonal segments
> correctly, so this is acceptable. For a fully orthogonal path add a fifth waypoint:
> `[from_port, (fx, mid_y), (bl - m, mid_y), (tx, mid_y), to_port]`.
> The 4-point form is simpler and sufficient for scoring accuracy.

> **Avoid**: `[from_port, (bl - m, mid_y), (bl - m, mid_y), to_port]` — the two
> identical middle points collapse the path to an L-shape with a diagonal first segment
> that can still clip the blocker.

Similarly fix the symmetric case for vertical alignment (`fx == tx`): when ports share
the same x-coordinate, replace the top/bottom candidates with paths that include a
horizontal step.

### Acceptance Criteria

- Left/right candidates do not collapse to a straight line that crosses the blocker.
- All four candidates form geometrically valid detour shapes.

---

## 3. Lower the Intersection Penalty to Enable Local Trade-offs

The intersection weight must be low enough that a short local path with one unavoidable
intersection can beat a long clean perimeter path when the locality and length penalties
are sufficiently large.

Suggested weight:

```python
INTERSECTION_WEIGHT = 5000
```

With this weight and the penalties below, a path that escapes the local bounds by
30+ grid units will accumulate a penalty large enough to lose to a locally-blocked path.

### Acceptance Criteria

- A locally-blocked short path beats a clean perimeter path of absurd length.
- Paths that cross many rooms are still heavily penalised relative to clean paths.

---

## 4. Penalize Escaping the Local Bounds

Paths that place waypoints or segments outside the local routing region receive a
distance-proportional penalty.

```python
escape_distance = sum of how far each waypoint exceeds the local bounds
escape_penalty  = escape_distance * ESCAPE_WEIGHT   # suggested: 500
```

This penalty stacks with the intersection penalty so that a perimeter path that also
clips rooms is always a last resort.

### Acceptance Criteria

- Waypoints inside the local bounds receive no penalty.
- Waypoints outside receive a penalty proportional to how far they escape.
- Combined with the lower intersection weight, this makes clean perimeter paths lose to
  slightly-blocked local paths.

---

## 5. Penalize Excessive Route Length

Add penalties when the path length significantly exceeds the direct room-to-room distance.

```python
direct_distance = distance(source_center, target_center)
detour_ratio    = path_length / direct_distance
```

Suggested thresholds:

```text
ratio ≤ 1.5   → no penalty
ratio 1.5–2.0 → mild    (ratio - 1.5) * 400
ratio 2.0–3.0 → moderate  200 + (ratio - 2.0) * 1000
ratio > 3.0   → severe  1200 + (ratio - 3.0) * 2000
```

### Acceptance Criteria

- Very long detours receive strong score penalties.
- Short local detours are preferred when all else is equal.

---

## 6. Penalize Excessive Bends

```python
bend_penalty = bend_count * 100
```

### Acceptance Criteria

- Cleaner paths are preferred over highly segmented routes.
- Excessive zig-zagging is discouraged.

---

## 7. Updated Route Scoring System

```python
score = (
    room_intersections * INTERSECTION_WEIGHT      # 5000
    + path_length * 10
    + bend_count * 100
    + escape_penalty                               # distance outside local bounds * 500
    + detour_ratio_penalty                         # tiered thresholds above
)
```

Where:

```text
Lower score wins.
```

Because the intersection weight (5000) is now lower than the maximum escape penalty for a
typical map-spanning route (30+ units × 500 = 15000+), a short local path with one
unavoidable intersection will beat a clean perimeter route. A path crossing two or more
rooms (10000+) still loses to any clean path.

### Acceptance Criteria

- Large perimeter loops become rare.
- Local routes are strongly preferred.
- Short readable paths consistently win.
- The scoring system is configurable via named constants.

---

## 8. Add Maximum Reasonable Route Constraints

Add a sanity limit to prevent absurd routes. If all candidates exceed these limits,
choose the least-bad route and mark it as problematic for debug visualization.

```python
MAX_DETOUR_RATIO = 5.0
MAX_BEND_COUNT   = 6
```

### Acceptance Criteria

- The router no longer generates map-spanning loops for nearby rooms.
- Failed routing attempts fall back gracefully to the shortest available candidate.
- Problematic routes are flagged for debug highlighting.

---

# Suggested Implementation Strategy

## Step 1: Add `get_local_bounds`

```python
def get_local_bounds(from_room, to_room, margin=ROUTE_BOUNDING_MARGIN) -> Rect:
    ...
```

## Step 2: Update `_score_path`

Add `local_bounds` and `direct_distance` optional parameters. Compute escape penalty and
detour ratio penalty. Lower `INTERSECTION_WEIGHT` to 5000.

## Step 3: Fix `route_detour` candidate generation

- Clamp all four waypoints to `local_bounds`.
- Fix left/right degenerate case when `fy == ty` (or `fx == tx`).
- Pass `local_bounds` and `direct_distance` into `_score_path`.

## Step 4: Update `route_orthogonal`

Pass `local_bounds` and `direct_distance` into `_score_path` so the improved scoring
applies to orthogonal candidates too.

## Step 5: Add constants

```python
ROUTE_BOUNDING_MARGIN = 4
INTERSECTION_WEIGHT   = 5000
ESCAPE_WEIGHT         = 500
MAX_DETOUR_RATIO      = 5.0
MAX_BEND_COUNT        = 6
```

## Step 6: Add Debug Visualization (existing capability — extend if needed)

The existing `debug_routing=True` flag in `GridRenderer` already highlights problematic
routes in EMBER. Extend to optionally draw the local bounds rectangle.

---

# Implementation Pitfalls

These are non-obvious issues discovered during spec validation against the Crucible map.

## Pitfall 1 — `ROUTE_BOUNDING_MARGIN` (4) vs `CONNECTION_OBSTACLE_MARGIN` (16)

The bypass offset `m = 16` far exceeds the local bounds expansion `margin = 4`, so
clamping fires on virtually every detour candidate.  This is **intentional and correct**:
the local bounds is computed from the bounding rect of *both* rooms, not just the blocker
edge.  In typical cases the blocker lies fully inside the local bounds, so the clamped
bypass position still clears the blocker's edge.

To verify: for a given connection, confirm that `bypass_top = min(bt + m, local_top) > bt`
(i.e. the clamped position is still above the blocker's top).  If it is not — the blocker
extends past the local bounds — the "accept locally-blocked path" fallback applies.

## Pitfall 2 — Only the first blocker shapes the candidates

`_find_blocking_room` returns the first blocking room found in the best orthogonal path.
The four detour candidates are geometrically shaped around *that one room*.  A second
blocker may still be clipped by some candidates.  Scoring counts all intersections
correctly, so the least-bad local candidate still wins.  This is pre-existing behaviour
and a non-goal to change.

## Pitfall 3 — `test_detour_ratio_within_limit` does not catch perimeter loops

All connections in the Crucible pass the detour-ratio test (ratio ≤ 5.0) even before
the fix, including the three failing ones (ratios 2.1–3.4).  The definitive acceptance
test is `test_route_stays_within_local_bounds` in
`tests/unit/map/test_routing_validation.py`.

## Pitfall 4 — Level 3 `r5 → r6` remains problematic after the fix

The Vault of Opportunities → Gravity Anomaly connection (Level 3) spans ~60 grid units
horizontally with large rooms `r7` and `r8` inside the local bounds.  After clamping,
all four detour candidates still intersect `r7` or `r8`.  `is_route_problematic` will
flag this connection as unresolved.  This is the intended "accept locally-blocked path"
behaviour, not a bug.

## Pitfall 5 — Degenerate case is absent from the Crucible fixture

No connection in `tests/fixtures/crucible.json` has `fy == ty` or `fx == tx` with a
blocker in between.  The degenerate-case fix (Req 2) is a correctness improvement for
other maps; it will not be exercised by the Crucible validation tests.  Add a synthetic
unit test in `tests/unit/map/test_routing.py` to cover this path directly.

---

# Edge Cases

The implementation should handle:

- Nearby rooms with one blocking room (most common — local fix should always work)
- Blocker that extends past the local bounds (accept locally-blocked path)
- Degenerate alignment: `fy == ty` or `fx == tx` (fix candidate generation)
- Diagonal room relationships
- Tight room clusters
- Sparse layouts
- Large boss rooms
- Long hallway-style maps
- Small maps with few routing options

---

# Non-Goals

This feature does not require:

- Perfect graph routing
- Full A* pathfinding
- Corridor generation
- Dynamic room repositioning
- Connection-to-connection collision avoidance

The goal is simply:

```text
Prefer clean local detours over giant perimeter loops.
```

---

# Definition of Done

This refinement is complete when:

- Detour waypoints are clamped to the local routing region.
- Left/right candidates do not degenerate when ports are horizontally aligned.
- The intersection weight is lowered to 5000 so local paths can beat clean perimeter routes.
- Escape, detour-ratio, and bend penalties are applied in scoring.
- Routed paths remain visually local in most cases.
- Nearby room connections no longer wrap around large portions of the map.
- The Crucible map produces visually reasonable room connections without giant perimeter routes.
- `pytest tests/unit/map/test_routing_validation.py` passes (currently 3 failures: L1/R1→R3,
  L1/R5→R2, L3/r5→r6 — L3/r5→r6 may remain flagged as problematic but must stay local).
- `pytest tests/unit/` green with all prior tests still passing.
