# Feature Spec: Obstacle-Aware Room Connection Routing

## Feature Name

Obstacle-Aware Dungeon Map Connection Routing

## Goal

Improve the Dungeon Daddy map viewer so that connection lines between rooms do not visually pass underneath or through unrelated rooms.

The dungeon layout is defined in JSON first. Rooms and their connections already exist as data. This feature should improve the rendering/layout behavior without requiring the level designer to manually draw every connection.

## Problem Statement

The current map renderer draws room connections as straight lines between rooms. In some layouts, those lines pass underneath or through rooms that are not part of the connection. This makes the dungeon map harder to read and can visually imply incorrect room relationships.

Example problem:

```text
R4 connects to R5, but the connection line crosses underneath R2.
```

The renderer should avoid this when possible by routing connections around room rectangles.

## Design Principle

Separate these two responsibilities:

```text
1. Room layout
2. Connection routing
```

The application should first determine where rooms are placed. After rooms are positioned, the renderer should calculate connection paths that avoid unrelated rooms.

## Existing Data Assumption

The level JSON already defines:

- Rooms
- Room IDs
- Room dimensions or display size
- Room positions, either explicit or generated
- Connections between rooms
- Connection type, such as door, arch, tunnel, secret, etc.

This feature should not require changing existing level JSON for basic behavior.

Optional JSON layout hints may be added later, but the first implementation should work automatically.

---

# Functional Requirements

## 1. Connect Room Edge-to-Edge Instead of Center-to-Center

Connection lines should not start or end at the center of a room.

Instead, each connection should start and end at a calculated room edge port.

Each room should support four basic ports:

```text
north
south
east
west
```

The renderer should choose ports based on the relative position of the connected rooms.

Examples:

```text
If target room is mostly to the right:
  source.east -> target.west

If target room is mostly below:
  source.south -> target.north
```

### Acceptance Criteria

- Connections originate from the edge of the source room.
- Connections terminate at the edge of the target room.
- Existing room selection behavior still works.
- Existing connection labels still render.
- Existing connection types still render using the current visual style.

---

## 2. Detect When a Connection Crosses an Unrelated Room

After calculating a connection path, the application should detect whether any segment intersects a room rectangle that is not the source room or target room.

For each connection:

```text
For each room:
  If room is source or target:
    ignore it
  Else:
    check whether the connection line intersects the room rectangle
```

This collision detection should work for:

- Straight line connections
- Orthogonal routed connections
- Multi-segment paths

### Acceptance Criteria

- The system can determine whether a connection path intersects an unrelated room.
- Source and target rooms are ignored during collision checks.
- The collision logic works with rectangular room bounds.
- The collision logic is isolated enough to be unit tested.

---

## 3. Add Orthogonal / Manhattan-Style Connection Routing

When a straight connection would cross an unrelated room, the renderer should attempt to route the connection using horizontal and vertical segments.

Preferred style:

```text
source port -> waypoint(s) -> target port
```

The first implementation should try simple two-segment routes:

```text
Option A:
horizontal first, then vertical

Option B:
vertical first, then horizontal
```

Example:

```text
source.east -> intermediate point -> target.west
```

If both options are valid, prefer the shorter route.

If one option crosses fewer rooms, prefer that option.

If both still cross rooms, choose the least-bad route and optionally mark it for debug visibility.

### Acceptance Criteria

- The renderer attempts orthogonal routing when a straight line intersects an unrelated room.
- The renderer tries both horizontal-first and vertical-first routing.
- The renderer chooses the route with fewer room intersections.
- If both routes avoid unrelated rooms, the renderer chooses the shorter or cleaner route.
- Connection labels remain readable and appear near the routed connection.
- The visual result should look appropriate for a dungeon map.

---

## 4. Support Multi-Segment Detours Around Blocking Rooms

If both simple orthogonal routes fail, the renderer should attempt a basic detour around the blocking room.

Given a blocking room rectangle, the renderer should try routing around:

```text
top side
bottom side
left side
right side
```

Use a configurable margin so the line does not hug the room boundary too tightly.

Suggested constant:

```python
CONNECTION_OBSTACLE_MARGIN = 16
```

Example route:

```text
source port
-> waypoint outside blocking room
-> waypoint past blocking room
-> target port
```

### Acceptance Criteria

- The renderer can create a multi-segment path around a blocking room.
- Detour paths include a visible margin around unrelated rooms.
- The renderer avoids routing directly along the room border.
- The feature handles at least one blocking room between source and target.
- If multiple rooms block a path, the renderer chooses the best available path using the current heuristic.

---

## 5. Add Optional Manual Waypoints in JSON

Automatic routing should be the default. However, the JSON should allow optional manual waypoints for hand-authored special cases.

Example:

```json
{
  "from": "R4",
  "to": "R5",
  "type": "door",
  "waypoints": [
    { "x": 22, "y": 14 },
    { "x": 30, "y": 14 }
  ]
}
```

If waypoints exist, the renderer should use them as part of the connection path.

Manual waypoints should be treated as layout hints, not as room connections.

### Acceptance Criteria

- Existing JSON without waypoints still works.
- A connection may optionally define waypoints.
- If waypoints are provided, the connection path uses them.
- Waypoints do not create new rooms.
- Waypoints do not alter graph connectivity.
- Manual waypoint paths are still checked for room intersections.

---

## 6. Add Debug Visualization for Routed Connections

Add a developer/debug option to make routing behavior easier to inspect.

Debug mode should be able to show:

- Connection ports
- Waypoints
- Routed path segments
- Blocking room detection
- Connections that could not be cleanly routed

This can be a temporary developer toggle or a formal map debug option.

### Acceptance Criteria

- A developer can visually inspect connection routes.
- Waypoints can be shown when debug mode is enabled.
- Problematic routes can be highlighted or logged.
- Debug visualization does not appear during normal play/view mode unless enabled.

---

# Suggested Implementation Approach

## Step 1: Add Geometry Helpers

Create helper functions for:

```python
get_room_rect(room)
get_room_port(room, direction)
line_intersects_rect(p1, p2, rect)
path_intersects_any_room(path, rooms, source_id, target_id)
calculate_path_length(path)
```

These should be small, testable functions.

## Step 2: Replace Center-to-Center Connections

Update the renderer so basic connection drawing uses edge ports instead of room centers.

## Step 3: Add Straight Path Validation

Before drawing a straight connection, test whether it crosses unrelated rooms.

If clean:

```text
draw straight edge-to-edge path
```

If blocked:

```text
try routed path
```

## Step 4: Add Simple Orthogonal Routing

Try:

```text
horizontal-first route
vertical-first route
```

Score each route based on:

```text
number of room intersections
path length
number of bends
```

Prefer:

```text
fewest intersections
then shortest length
then fewest bends
```

## Step 5: Add Detour Routing

If the simple routes fail, generate candidate detours around blocking rooms.

Score each candidate the same way.

## Step 6: Add Optional JSON Waypoint Support

If a connection has manual waypoints, include them between the source and target ports.

## Step 7: Add Tests

Add unit tests for the geometry and routing logic.

---

# Suggested Route Scoring

Use a simple scoring model:

```python
score = (
    room_intersections * 10000
    + path_length
    + bend_count * 25
)
```

Lower score wins.

This strongly prioritizes avoiding room intersections.

---

# Edge Cases

The implementation should handle:

- Rooms directly beside each other
- Rooms stacked vertically
- Diagonal room relationships
- Large rooms blocking a connection
- Multiple nearby rooms
- Connections involving boss rooms, vault rooms, shrines, traps, or elevators
- Secret connections
- Manual waypoints
- Very small levels with only a few rooms
- Larger generated levels with many rooms

---

# Non-Goals for First Implementation

Do not attempt a full graph layout engine yet.

This feature does not need to solve:

- Perfect automatic dungeon layout
- Force-directed graph layout
- Automatic room repositioning
- Corridor carving in a tile map
- Avoiding connection-to-connection crossings
- Advanced A* routing over a grid

Those may be future enhancements.

The first goal is simple:

```text
Connection lines should not pass through unrelated room rectangles when a reasonable routed path is available.
```

---

# Future Enhancements

Possible later improvements:

- A* routing over a coarse grid
- Room auto-positioning based on graph topology
- Edge bundling for parallel routes
- Better label placement along routed paths
- User-editable waypoints in the UI
- Persisted layout edits back into JSON
- Separate visual corridors from logical connections
- Validation warnings in the dungeon design panel

---

# Definition of Done

This feature is complete when:

- Connections are drawn from room edge ports instead of room centers.
- The renderer detects when a connection crosses an unrelated room.
- The renderer automatically routes around unrelated rooms when practical.
- Manual connection waypoints are supported in JSON.
- The routing code is testable and covered by unit tests.
- Debug visualization or logging exists for failed/problematic routes.
- Existing Dungeon Daddy level JSON files continue to load.
- The Level 1 Crucible map no longer shows connection lines passing underneath unrelated rooms in normal viewing mode.
