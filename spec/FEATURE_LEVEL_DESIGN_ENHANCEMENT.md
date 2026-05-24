# Dungeon Daddy – Dungeon Map Layout, Interaction, Loop Semantics, and Validation Specification

## Purpose

Define requirements for dungeon map rendering, interaction, loop modeling, validation, and LLM integration.

This specification is intended to be used directly by Claude Code for implementation using TDD.

---

## Core Design Principle

Separate dungeon structure from visual layout.

- JSON defines:
    - rooms
    - connections
    - loops
- Renderer determines:
    - spacing
    - positioning
    - visual clarity

The renderer must prioritize readability over compactness.

---

## Implementation Scope

Implement:

1. Layout engine improvements
2. Connection rendering and labeling
3. Connection interaction
4. Loop data model and semantics
5. Dungeon validation system
6. LLM validator integration

---

## 1. Room Layout Rules

### Requirements

- Rooms must not overlap
- Rooms must not touch edges
- Enforce minimum spacing between rooms
- Layout must allow space for connection lines and labels

### Implementation Notes

- Introduce `MIN_ROOM_SPACING`
- Use bounding box collision detection
- Renderer may adjust layout positions for clarity

### Acceptance Criteria

- No overlapping rooms
- No edge-touching rooms
- All rooms have visible spacing
- Layout supports connection rendering without clutter

---

## 2. Connection Rendering

### Requirements

- Render connections as visible lines between rooms
- Lines connect logical points (center or edge midpoint)

### Labeling

- Each connection must display a label
- Label source: connection `type` or name
- If too long:
    - Truncate with `...` OR abbreviate

### Placement

- Labels placed near connection line
- Avoid overlapping room labels when possible

### Acceptance Criteria

- All connections are visible
- All connections are labeled
- Labels are readable or safely truncated

---

## 3. Connection Interaction

### Requirements

- Connection lines must be selectable
- Clicking a connection logs information to chat
- Behavior mirrors room selection

### Logged Data

- Source room ID and name
- Target room ID and name
- Connection type
- Connection note
- Loop participation (main/sub)

### Acceptance Criteria

- Connections are clickable
- Correct data is logged
- Room interaction remains unchanged

---

## 4. Loop Data Model and Semantics

### Level JSON Structure

```json
"loops": [
  {
    "id": "string",
    "type": "main" | "sub",
    "explanation": "string",
    "entry": "room_id",
    "goal": "room_id",
    "path_a": ["room_id"],
    "path_b": ["room_id"],
    "rooms": ["room_id"]
  }
]
```

---

### 4.1 Main Loop

#### Requirements

- Exactly one main loop must exist
- Must include an explanation

#### Room Requirements

```json
"main_loop_role": "string"
```

#### Acceptance Criteria

- Main loop exists
- Explanation is present and meaningful
- All rooms in main loop define `main_loop_role`

---

### 4.2 Sub-Loops

#### Requirements

- Zero or more sub-loops allowed
- Each must include explanation and rooms

#### Room Requirements

```json
"sub_loop_roles": [
  {
    "loop_id": "string",
    "role": "string"
  }
]
```

#### Acceptance Criteria

- All sub-loops include explanations
- All referenced rooms exist
- Rooms define roles for each sub-loop they participate in

---

### Acceptance Criteria (Loops Overall)

- Exactly one main loop exists
- All loops include explanations
- Entry and goal rooms are valid
- Paths reference valid rooms
- Loop definitions are internally consistent
- Rooms include appropriate loop role metadata

---

## 5. Dungeon Validation System

### Requirements

Implement:

```python
validate_dungeon(level_json) -> ValidationResult
```

---

### Validation Rules

#### Layout

- No overlapping rooms
- No edge-touching rooms
- Minimum spacing enforced

#### Connections

- All referenced rooms exist
- Connections are valid pairs
- Each connection has a label/type

#### Loops

- Exactly one main loop exists
- Loop room references are valid
- Entry and goal rooms exist
- Loop explanations exist
- Paths are continuous and valid

#### Room Loop Roles

- Main loop rooms must include `main_loop_role`
- Sub-loop rooms must include `sub_loop_roles`
- Loop IDs must match valid loops

---

### Output Format

```json
{
  "valid": false,
  "errors": [
    {
      "code": "ROOMS_TOUCHING",
      "message": "Rooms R1 and R2 are touching",
      "room_ids": ["R1", "R2"]
    }
  ],
  "warnings": []
}
```

---

### Acceptance Criteria

- Invalid layouts are detected
- Invalid connections are detected
- Missing loop data is detected
- Invalid references are detected
- Output is structured and machine-readable

---

## 6. LLM Validator Integration

### Requirements

The dungeon generator must use the validator.

### Behavior

1. Generate dungeon JSON
2. Call validator
3. If invalid:
    - Revise output
    - Re-validate
4. Repeat until valid or limit reached

---

### LLM Constraints

- Prefer readability over compact layouts
- Must enforce room spacing
- Must include loop explanations
- Must include room loop roles
- Must pass validation before returning output

---

### Acceptance Criteria

- LLM calls validator before final output
- Invalid outputs are corrected automatically
- Final output always passes validation
- Generated dungeons include complete loop metadata

---

## 7. Rendering Responsibilities

### Data Layer

Defines:

- rooms
- connections
- loops
- metadata

### Renderer

Responsible for:

- layout spacing
- positioning
- drawing
- interaction

### Requirement

Renderer may adjust layout for clarity but must preserve logical relationships.

---

## 8. TDD Requirements

### Requirements

- Implement using TDD
- Write failing tests first for:
    - room spacing violations
    - missing connection labels
    - connection interaction
    - missing loop explanations
    - missing loop roles
    - invalid loop definitions

### Acceptance Criteria

- Tests fail before implementation
- Tests pass after implementation
- Existing functionality remains intact

---

## 9. Final Acceptance Criteria

A dungeon level is valid when:

- Rooms do not overlap or touch
- Connections are visible and labeled
- Connections are interactive
- Main loop is defined and explained
- Sub-loops are defined and explained
- All loop-participating rooms define roles
- Validator passes with no errors
- LLM consistently produces valid dungeons
