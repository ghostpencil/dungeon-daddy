# Dungeon Daddy — Graph Mode Phase 2.5: Semantic Metadata Backfill and Validation

## Purpose

Phase 1 made Graph Mode geometrically stable and readable.

Phase 2 made Graph Mode visually semantic by introducing role-based room styling, connection styling, critical path emphasis, endpoint emphasis, and visual hierarchy feedback.

Phase 2.5 exists to improve the quality of that semantic layer by updating existing dungeon data with explicit metadata instead of relying too heavily on name inference.

The key goal is to reduce avoidable `unknown` room roles and ambiguous endpoints for the two active evaluation dungeons:

- `The Crucible`
- `Tomb of the Forgotten King`

This phase should update both test fixtures and existing local dungeon maps in:

```text
C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons
```

Only those two dungeons matter for this phase.

Do not update unrelated dungeon files unless a test fixture depends on them directly.

---

## Current Context

Graph Mode is the active improved renderer.

Grid Mode must remain untouched. It is intentionally preserved as a baseline comparison view against the new Graph Mode. Do not modify Grid Mode rendering, Grid Mode layout data, or Grid Mode behavior.

The current Phase 2 reports show that geometry is stable, but semantic scores are limited by missing or ambiguous metadata. In particular:

- several rooms still resolve to `unknown`
- some endpoint rooms are not identified as `exit`, `descent`, `objective`, `boss`, or `transition`
- some critical paths are inferred, but not explicitly supported by dungeon-authored metadata
- some connection styles remain generic because connection metadata is too vague

Phase 2.5 should not replace the role inference system. Instead, it should allow explicit metadata to override or improve inference when map intent is known.

---

## High-Level Requirement

Add, support, and backfill enhanced semantic metadata for Graph Mode dungeon rendering.

The system should support explicit metadata on rooms, connections, and dungeon/floor-level layout structures. Existing dungeons should be migrated in a safe, additive, backward-compatible way.

The target outcome is:

```text
Fewer unknown room roles.
Clearer entrances.
Clearer endpoints.
Clearer objective/descent/boss/key/hazard roles.
Better semantic scores.
No regression in geometry scores.
No Grid Mode changes.
No breaking JSON compatibility.
```

---

## Design Principles

1. **Metadata should be additive.**
   Existing dungeon JSON should remain readable by older code paths where possible.

2. **Explicit metadata wins over inference.**
   If a room declares `layout_role`, `room_role`, or equivalent supported metadata, the semantic system should use that before name-based inference.

3. **Inference remains the fallback.**
   Name inference is still useful for generated or incomplete content.

4. **Unknown is still valid.**
   Do not force certainty. If a room truly has no semantic role, `unknown` is acceptable.

5. **Important ambiguity should be visible.**
   Reports should clearly distinguish harmless `unknown` rooms from problematic unknowns, such as an unknown endpoint or unknown critical-path destination.

6. **Graph Mode only.**
   Do not alter Grid Mode behavior.

7. **Current dungeon maps matter.**
   Update both test fixtures and existing local dungeon files for `The Crucible` and `Tomb of the Forgotten King`.

---

## Proposed Metadata Schema

Use the existing project style and JSON conventions where possible. Do not introduce a large, incompatible schema rewrite.

The following structure is recommended. If the existing dungeon JSON format already has comparable fields, adapt to that format instead of duplicating fields unnecessarily.

### Room-Level Metadata

Each room should support semantic metadata such as:

```json
{
  "id": "R2",
  "name": "Marketplace",
  "layout_role": "hub",
  "visual_priority": "high",
  "critical_path": true,
  "graph_notes": "Central organizing room for the floor."
}
```

Recommended fields:

| Field | Type | Required | Purpose |
|---|---|---:|---|
| `layout_role` | string | no | Explicit role used by Graph Mode semantic styling. |
| `visual_priority` | string | no | Optional manual priority: `low`, `medium`, `high`, `major`. |
| `critical_path` | boolean | no | Marks room as part of the floor's main route. |
| `optional_branch` | boolean | no | Marks side content. |
| `graph_notes` | string | no | Human-readable explanation for future maintenance. |

Supported `layout_role` values should align with Phase 2 vocabulary:

```text
entrance
hub
boss
objective
exit
descent
elevator
stairs
key_room
lock_room
treasure
hazard
secret
corridor
hall
library
forge
utility
study
transition
side_room
unknown
```

Do not invent new role names unless absolutely necessary. If a new role is introduced, update the resolver, tests, and documentation.

### Connection-Level Metadata

Each connection should support semantic metadata such as:

```json
{
  "from": "R2",
  "to": "R4",
  "type": "door",
  "layout_connection_role": "critical",
  "connection_style": "normal"
}
```

Recommended fields:

| Field | Type | Required | Purpose |
|---|---|---:|---|
| `layout_connection_role` | string | no | `critical`, `optional`, `secret`, `locked`, `vertical`, `shortcut`, `normal`. |
| `connection_style` | string | no | Explicit style override for Graph Mode. |
| `critical_path` | boolean | no | Marks the connection as part of the main path. |
| `graph_notes` | string | no | Human-readable explanation. |

Supported connection styles should include:

```text
normal
critical
optional
secret
locked
vertical
shortcut
hazard
```

Existing connection labels such as `door`, `hall`, `arch`, `hole`, `secret_shortcut`, and `lock_key` should still work.

Explicit metadata should take precedence over label aliases.

### Floor-Level Metadata

Each floor should support optional graph layout metadata:

```json
{
  "layout_metadata": {
    "graph_template": "hub_spoke",
    "entrance_room_id": "r01",
    "endpoint_room_id": "r06",
    "objective_room_ids": ["r03"],
    "critical_path": ["r01", "r02", "r05", "r06"],
    "optional_branches": [["r02", "r04"]],
    "notes": "Factory floor organized around Central Hub. Maintenance Tunnel is the forward transition."
  }
}
```

Recommended fields:

| Field | Type | Required | Purpose |
|---|---|---:|---|
| `graph_template` | string | no | Explicit layout template hint. |
| `entrance_room_id` | string | no | Explicit floor start. |
| `endpoint_room_id` | string | no | Explicit floor endpoint/destination. |
| `objective_room_ids` | array | no | Key objective rooms. |
| `critical_path` | array | no | Ordered list of room IDs for primary route. |
| `optional_branches` | array of arrays | no | Ordered optional route fragments. |
| `notes` | string | no | Human-readable design intent. |

Supported `graph_template` values should remain consistent with previous phases:

```text
linear
freeform
hub_spoke
branch_and_merge
lock_key
split_path
boss_endcap
loop
```

---

## Existing Dungeon Backfill Scope

Update only the following local dungeons:

```text
C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons\The Crucible*
C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons\Tomb of the Forgotten King*
```

The exact filenames may vary. Search the folder for dungeon JSON files whose display name or dungeon name matches:

```text
The Crucible
Tomb of the Forgotten King
```

If the local dungeon directory is not available in the execution environment, do not fail silently. Produce a clear report stating:

```text
LOCAL_DUNGEON_DIRECTORY_NOT_FOUND
```

and still update repository test fixtures.

---

## Suggested Metadata Backfill: The Crucible

Use the existing room names and IDs from the current fixtures and local dungeon files. Do not assume every local file exactly matches the fixture IDs; match by ID when possible, then by room name when necessary.

### The Crucible — Level 1

Known rooms from current fixture:

| Room | Suggested Role | Priority | Notes |
|---|---|---|---|
| `Receiving Hall` / `R1` | `entrance` | medium | Floor entry point. |
| `Marketplace` / `R2` | `hub` | high | Central organizing room. |
| `Cargo Bay` / `R3` | `utility` or `side_room` | low | Ordinary supporting room unless dungeon text says otherwise. |
| `Elevator Shaft` / `R4` | `descent` or `elevator` | medium | Floor transition/destination. |
| `Trap Room` / `R5` | `hazard` | medium | Danger room. |

Recommended floor metadata:

```json
{
  "graph_template": "freeform",
  "entrance_room_id": "R1",
  "endpoint_room_id": "R4",
  "critical_path": ["R1", "R2", "R4"]
}
```

Expected improvement:

- no missing entrance role warning
- no missing objective/endpoint warning if `descent` is accepted as endpoint
- `Elevator Shaft` should receive endpoint emphasis
- `Marketplace` should remain visually high priority

### The Crucible — Level 2

Known rooms from current fixture:

| Room | Suggested Role | Priority | Notes |
|---|---|---|---|
| `Entry Chamber` / `r01` | `entrance` | medium | Floor entry point. |
| `Central Hub` / `r02` | `hub` | high | Hub-spoke anchor. |
| `Conveyor Control` / `r03` | `key_room` | medium | Key/control objective. |
| `Arcane Power Room` / `r04` | `utility` or `objective` | medium | Power/control support; use `objective` only if design text supports it. |
| `Molten Metal Pit` / `r05` | `hazard` | medium | Hazard. |
| `Maintenance Tunnel` / `r06` | `transition` or `exit` | medium | Forward transition/endpoint for this floor. |

Recommended floor metadata:

```json
{
  "graph_template": "hub_spoke",
  "entrance_room_id": "r01",
  "endpoint_room_id": "r06",
  "objective_room_ids": ["r03"],
  "critical_path": ["r01", "r02", "r05", "r06"],
  "optional_branches": [["r02", "r03"], ["r02", "r04"]]
}
```

Expected improvement:

- semantic score should rise significantly above the current weak score
- `Maintenance Tunnel` should no longer be an unknown endpoint
- `Conveyor Control` should remain legible as a key room
- `Central Hub` should remain the visual anchor

### The Crucible — Level 3

Known rooms from current fixture:

| Room | Suggested Role | Priority | Notes |
|---|---|---|---|
| `Control Nexus` / `r1` | `key_room` or `entrance` depending design intent | medium | Currently key room; if this is the start of the floor, mark entrance too via floor metadata. |
| `Conduit Corridor` / `r2` | `corridor` | low | Passage. |
| `Crystal Array` / `r3` | `objective` or `utility` | medium | Power system/objective support. |
| `Electrified Floor` / `r4` | `hazard` | medium | Hazard. |
| `Vault of Opportunities` / `r5` | `treasure` | medium | Treasure/boon. |
| `Gravity Anomaly` / `r6` | `hazard` | medium | Hazard. |
| `Prime Golem Lair` / `r7` | `boss` | high | Boss encounter. |
| `Power Core Chamber` / `r8` | `objective` or `boss` | major | Final objective / power core destination. |

Recommended floor metadata:

```json
{
  "graph_template": "linear",
  "entrance_room_id": "r1",
  "endpoint_room_id": "r8",
  "objective_room_ids": ["r3", "r8"],
  "critical_path": ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8"]
}
```

Important note:

The current endpoint detector selected `Prime Golem Lair` as endpoint because boss priority outranked the later room. This phase should allow floor-level `endpoint_room_id` to override automatic endpoint detection. If `Power Core Chamber` is the true destination, it should be emphasized as the endpoint even if `Prime Golem Lair` remains visually high priority as a boss.

Expected improvement:

- no missing entrance warning
- endpoint should be `Power Core Chamber`, not `Prime Golem Lair`, when explicit metadata says so
- both boss and objective styling should remain clear
- the final destination should feel distinct from the boss room

---

## Suggested Metadata Backfill: Tomb of the Forgotten King

Use the existing room names and IDs from the current fixtures and local dungeon files. Match by ID when possible, then by room name.

### Tomb of the Forgotten King — Current Tested Floor / Tomb L1

Known rooms from current fixture:

| Room | Suggested Role | Priority | Notes |
|---|---|---|---|
| `Flooded Entry` / `1-A` | `entrance` | medium | Floor entry point. |
| `Drowned Shrine` / `1-B` | `objective`, `side_room`, or `study` | medium/low | Choose based on available design text. Shrine likely merits semantic role if important. |
| `Rat Warren` / `1-C` | `hazard` or `side_room` | low/medium | Likely hazard/side area. |
| `Collapsed Gallery` / `1-D` | `hall` or `corridor` | low | Passage/gallery. |
| `Descent Chamber` / `1-E` | `descent` | medium | Floor transition/destination. |

Recommended floor metadata:

```json
{
  "graph_template": "freeform",
  "entrance_room_id": "1-A",
  "endpoint_room_id": "1-E",
  "critical_path": ["1-A", "1-B", "1-D", "1-E"],
  "optional_branches": [["1-A", "1-C", "1-E"]]
}
```

Expected improvement:

- fewer unknown room roles
- `Descent Chamber` should be explicit endpoint
- `Rat Warren` should read as optional/hazard branch if supported by the graph
- semantic score should improve over current score

### Tomb of the Forgotten King — Other Known Floors

Earlier screenshots included rooms such as:

- `Stair Landing`
- `Servants' Hall`
- `Scriptorium`
- `Reliquary`
- `Wraith's Study`
- `Sealed Descent`
- `Ossuary Approach`
- `Advisor's Nook`
- `Golem Forge`
- `Processional`
- `Throne of Bone`

If these maps exist in the local dungeon file, backfill metadata using the following guidance.

#### Hall of Bound Servants

Suggested roles:

| Room | Suggested Role |
|---|---|
| `Stair Landing` | `entrance` or `stairs` |
| `Servants' Hall` | `hall` |
| `Scriptorium` | `library` |
| `Reliquary` | `treasure` or `objective` |
| `Wraith's Study` | `study` or `boss` if encounter-focused |
| `Sealed Descent` | `descent` or `exit` |

Suggested floor metadata:

```json
{
  "graph_template": "freeform",
  "entrance_room_id": "2-A",
  "endpoint_room_id": "2-F",
  "critical_path": ["2-A", "2-C", "2-E", "2-F"]
}
```

Adjust room IDs to match the actual dungeon file.

#### The King's Tomb

Suggested roles:

| Room | Suggested Role |
|---|---|
| `Ossuary Approach` | `entrance` or `hall` |
| `Advisor's Nook` | `study` or `side_room` |
| `Golem Forge` | `forge` or `hazard` |
| `Processional` | `hall` or `corridor` |
| `Throne of Bone` | `boss` or `objective` |

Suggested floor metadata:

```json
{
  "graph_template": "branch_and_merge",
  "entrance_room_id": "3-A",
  "endpoint_room_id": "3-E",
  "critical_path": ["3-A", "3-D", "3-E"],
  "optional_branches": [["3-A", "3-C", "3-D"], ["3-A", "3-B", "3-D"]]
}
```

Adjust room IDs to match the actual dungeon file.

---

## Required Code Changes

### 1. Metadata Reading

Update the semantic role resolution pipeline so it checks sources in this order:

1. explicit room metadata field, such as `layout_role`
2. existing room role/type fields, if any
3. floor-level special references, such as `entrance_room_id`, `endpoint_room_id`, and `objective_room_ids`
4. name-based inference
5. `unknown`

Endpoint detection should check sources in this order:

1. explicit `layout_metadata.endpoint_room_id`
2. explicit room role priority: `objective`, `boss`, `exit`, `descent`, `elevator`, `stairs`, `transition`
3. inferred endpoint from graph position
4. previous fallback behavior

Critical path detection should check sources in this order:

1. explicit `layout_metadata.critical_path`
2. explicit room/connection `critical_path` flags
3. existing inferred critical path

Connection style resolution should check sources in this order:

1. explicit `connection_style`
2. explicit `layout_connection_role`
3. existing connection type/label alias
4. normal style

### 2. Metadata Migration / Backfill Utility

Create a safe utility or script that can update dungeon JSON files with semantic metadata.

Suggested script name:

```text
scripts/backfill_graph_metadata.py
```

The script should support:

```bash
python scripts/backfill_graph_metadata.py --target-fixtures
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King"
python scripts/backfill_graph_metadata.py --dry-run
python scripts/backfill_graph_metadata.py --write
```

Required behavior:

- dry run by default unless `--write` is supplied
- creates timestamped `.bak` backups before modifying local dungeon files
- only modifies matching target dungeons
- preserves existing unknown/custom fields
- does not reorder large JSON structures unnecessarily if avoidable
- outputs a migration report

### 3. Metadata Validation

Add validation that detects:

- invalid `layout_role`
- invalid `visual_priority`
- invalid `graph_template`
- invalid `connection_style`
- `entrance_room_id` not found
- `endpoint_room_id` not found
- room IDs in `critical_path` not found
- duplicate room IDs in `critical_path`
- endpoint exists but has no endpoint-compatible role
- critical path does not start with entrance when entrance is explicit
- critical path does not end with endpoint when endpoint is explicit
- connection marked critical but not represented in the critical path

Validation should produce warnings, not immediate fatal errors, unless the malformed metadata would crash rendering.

### 4. Feedback Report Enhancements

Update layout feedback reports to include a new section:

```json
"metadata_quality_feedback": {
  "explicit_room_role_count": 0,
  "inferred_room_role_count": 0,
  "unknown_room_role_count": 0,
  "explicit_connection_style_count": 0,
  "inferred_connection_style_count": 0,
  "explicit_critical_path": true,
  "explicit_endpoint": true,
  "explicit_entrance": true,
  "metadata_score": 0.0,
  "warnings": []
}
```

The exact schema may vary, but it must provide enough information to assess whether Phase 2.5 improved semantic authoring.

### 5. Summary Report Enhancements

Update the Markdown summary report to include:

| Fixture/Dungeon | Geometry Score | Semantic Score | Metadata Score | Unknown Roles | Explicit Entrance | Explicit Endpoint | Explicit Critical Path | Warnings | Status |
|---|---:|---:|---:|---:|---|---|---|---|---|

---

## Required Test Updates

### Unit Tests

Add or update tests for:

1. explicit `layout_role` overrides name inference
2. explicit floor `entrance_room_id` marks entrance even when name does not imply entrance
3. explicit floor `endpoint_room_id` overrides automatic endpoint detection
4. explicit `critical_path` overrides inferred critical path
5. explicit connection style overrides label-based style
6. invalid metadata generates warnings
7. unknown role remains allowed when no metadata or inference exists
8. Grid Mode remains untouched

### Integration Tests

Add integration tests for:

1. `The Crucible` fixture metadata backfill
2. `Tomb of the Forgotten King` fixture metadata backfill
3. Phase 2 feedback still generated after metadata backfill
4. metadata quality feedback generated
5. semantic score improves or does not regress for target fixtures
6. geometry score remains 100 or does not regress from Phase 2 baseline
7. explicit endpoint works for Crucible Level 3: `Power Core Chamber` should be endpoint if metadata says so
8. Crucible Level 2 semantic score improves after `Maintenance Tunnel` is marked as transition/exit endpoint

### Local Dungeon File Tests / Checks

Where possible, add a test or script check that validates local dungeon file migration without requiring the exact developer machine path to exist.

Behavior should be:

- if local directory exists, validate and optionally migrate the two target dungeons
- if local directory does not exist, report `LOCAL_DUNGEON_DIRECTORY_NOT_FOUND` and continue fixture tests
- do not fail CI only because the local user dungeon directory is absent

---

## Required Output Artifacts

Claude Code must produce the following artifacts for assessment.

Place artifacts under:

```text
artifacts/layout/phase2_5/
```

### 1. Updated Graph Mode Screenshots

Generate PNGs for the target fixtures after metadata backfill:

```text
artifacts/layout/phase2_5/crucible_l1_graph.png
artifacts/layout/phase2_5/crucible_l2_graph.png
artifacts/layout/phase2_5/crucible_l3_graph.png
artifacts/layout/phase2_5/tomb_l1_graph.png
```

If additional Tomb of the Forgotten King floors are present and can be rendered, also generate:

```text
artifacts/layout/phase2_5/tomb_l2_graph.png
artifacts/layout/phase2_5/tomb_l3_graph.png
```

### 2. Updated Layout Feedback JSON

Generate feedback reports for each rendered fixture:

```text
artifacts/layout/phase2_5/crucible_l1.layout_feedback.json
artifacts/layout/phase2_5/crucible_l2.layout_feedback.json
artifacts/layout/phase2_5/crucible_l3.layout_feedback.json
artifacts/layout/phase2_5/tomb_l1.layout_feedback.json
```

Include both:

- `visual_hierarchy_feedback`
- `metadata_quality_feedback`

### 3. Metadata Migration Report

Generate:

```text
artifacts/layout/phase2_5/metadata_migration_report.md
```

The report must include:

- which fixture files were updated
- which local dungeon files were found
- which local dungeon files were updated
- whether backups were created
- which rooms changed from `unknown` to explicit roles
- which endpoints were explicitly set
- which critical paths were explicitly set
- any local directory errors
- any skipped files and why

### 4. Summary Report

Generate:

```text
artifacts/layout/phase2_5/layout_feedback_summary.md
```

This should include:

- Geometry Score
- Semantic Score
- Metadata Score
- Unknown Role Count
- Explicit Entrance
- Explicit Endpoint
- Explicit Critical Path
- Visual Warnings
- Metadata Warnings
- Pass/Fail status

### 5. Implementation Summary

Generate:

```text
artifacts/layout/phase2_5/implementation_summary.md
```

This should explain:

- files changed
- schema decisions
- migration behavior
- backup behavior
- tests added
- commands run
- test results
- known limitations
- whether Grid Mode was untouched

### 6. Optional Before/After Comparison

If practical, generate:

```text
artifacts/layout/phase2_5/before_after_summary.md
```

Compare Phase 2 vs Phase 2.5:

- semantic scores
- metadata scores
- unknown role counts
- endpoint detection changes
- notable visual changes

---

## Acceptance Criteria

Phase 2.5 is successful if all of the following are true:

1. Graph Mode still renders all target fixtures.
2. Grid Mode remains untouched.
3. Geometry score does not regress for target fixtures.
4. Metadata is explicit for known entrances in target fixtures.
5. Metadata is explicit for known endpoints in target fixtures.
6. Critical paths are explicit for target fixtures where design intent is known.
7. `The Crucible` Level 2 no longer treats `Maintenance Tunnel` as an unknown endpoint.
8. `The Crucible` Level 3 can explicitly treat `Power Core Chamber` as the endpoint, even though `Prime Golem Lair` remains a boss room.
9. `Tomb of the Forgotten King` tested floor explicitly treats `Descent Chamber` as endpoint/descent.
10. Semantic scores improve or stay the same for all target fixtures.
11. Unknown role count decreases for target fixtures unless the room is deliberately left unknown.
12. Metadata quality feedback appears in JSON reports.
13. Summary report includes metadata quality columns.
14. Backfill script can run in dry-run mode.
15. Backfill script creates backups before writing local dungeon files.
16. If the local dungeon directory is absent, the artifact report clearly says so without failing unrelated tests.
17. Unit tests pass.
18. Integration tests pass.
19. Type checking passes if currently part of the project workflow.
20. Generated artifacts are present under `artifacts/layout/phase2_5/`.

---

## Human Review Questions

After implementation, the generated artifacts should allow review of the following:

### The Crucible Level 1

- Does `Receiving Hall` clearly read as the entrance?
- Does `Marketplace` still read as the hub?
- Does `Elevator Shaft` read as the floor transition/destination?
- Does `Trap Room` read as a hazard?
- Did metadata improve clarity without adding visual noise?

### The Crucible Level 2

- Does `Central Hub` still anchor the layout?
- Does `Conveyor Control` read as a key/control room?
- Does `Maintenance Tunnel` now read as a transition or endpoint rather than an unknown ordinary room?
- Did the semantic score improve meaningfully?

### The Crucible Level 3

- Does `Control Nexus` read as the start/key control point?
- Does `Power Core Chamber` read as the final endpoint/objective?
- Does `Prime Golem Lair` still read as a boss encounter?
- Are boss and objective visually distinct enough?
- Did explicit endpoint metadata override automatic boss-priority endpoint detection correctly?

### Tomb of the Forgotten King

- Does `Flooded Entry` read as the entrance?
- Does `Descent Chamber` read as the destination?
- Do `Rat Warren`, `Drowned Shrine`, and `Collapsed Gallery` have reasonable roles?
- If additional floors are migrated, do `Sealed Descent` and `Throne of Bone` read as destinations?

### Overall

- Did Graph Mode become easier to understand at a glance?
- Did metadata reduce ambiguity?
- Are there fewer `unknown` roles?
- Did any explicit metadata make the layout misleading?
- Does Graph Mode remain cleaner and more useful than Grid Mode for overview reading?

---

## Commands to Run

Use the project’s actual commands where they differ, but the final implementation summary should include exact commands run.

Suggested commands:

```bash
python scripts/backfill_graph_metadata.py --target-fixtures --dry-run
python scripts/backfill_graph_metadata.py --target-fixtures --write
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --dry-run
python scripts/backfill_graph_metadata.py --local-dungeon-dir "C:\Users\ljfan\AppData\Local\DungeonDaddy\dungeons" --dungeons "The Crucible" "Tomb of the Forgotten King" --write
pytest
mypy .
```

If local write is unsafe or unavailable in the environment, run dry-run and document why write was not performed.

---

## Do Not Do

Do not:

- modify Grid Mode
- replace Graph Mode with tiles
- rewrite all dungeon JSON by hand without a repeatable migration utility
- remove name inference
- force all unknown roles into arbitrary roles
- fail CI because the local user dungeon folder does not exist
- change unrelated dungeons
- alter gameplay semantics unless the metadata clearly expresses existing design intent
- break old dungeon loading

---

## Final Deliverable

At the end of Phase 2.5, provide:

1. changed code
2. updated target fixtures
3. migrated local dungeons if available and writable
4. backup files for local dungeon writes
5. generated screenshots
6. layout feedback JSON files
7. metadata migration report
8. layout feedback summary
9. implementation summary
10. passing test/type-check results

The human assessment should be able to answer this question from the artifacts alone:

```text
Did explicit semantic metadata make Graph Mode more accurate, less ambiguous, and more useful without harming the clean Phase 1/2 layout improvements?
```
