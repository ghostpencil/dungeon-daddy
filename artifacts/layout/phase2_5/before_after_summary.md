# Phase 2 vs Phase 2.5 — Before/After Comparison

Generated: 2026-05-30

---

## Score Comparison

| Fixture | Phase 2 Semantic | Phase 2.5 Semantic | Delta | Phase 2 Metadata | Phase 2.5 Metadata | Unknown Roles (Before → After) |
|---|---:|---:|---:|---:|---:|---|
| crucible_l1 | 78.0 | 78.0 | 0 | N/A | 85.0 | 1 → 0 |
| crucible_l2 | 51.3 | 82.2 | **+30.9** | N/A | 85.0 | 2 → 0 |
| crucible_l3 | 78.4 | 82.8 | **+4.4** | N/A | 85.0 | 3 → 0 |
| tomb_l1 | 67.0 | 81.0 | **+14.0** | N/A | 85.0 | 3 → 0 |

`metadata_quality_feedback` did not exist in Phase 2. All four fixtures report 85.0 in Phase 2.5.

---

## Geometry Score

Geometry score held at **100.0** for all fixtures in both phases. No regression.

---

## Unknown Role Count

Phase 2 produced 9 `unknown` room roles across the four fixtures. Phase 2.5 eliminated all of them.

| Fixture | Unknown Rooms (Phase 2) | Resolution (Phase 2.5) |
|---|---|---|
| crucible_l1 | R3 Cargo Bay | → `side_room` |
| crucible_l2 | r04 Arcane Power Room | → `utility` |
| crucible_l2 | r06 Maintenance Tunnel | → `transition` |
| crucible_l3 | r2 Conduit Corridor | → `corridor` |
| crucible_l3 | r3 Crystal Array | → `objective` |
| crucible_l3 | r8 Power Core Chamber (was `boss`) | → `objective` (role corrected) |
| tomb_l1 | 1-B Drowned Shrine | → `objective` |
| tomb_l1 | 1-C Rat Warren | → `hazard` |
| tomb_l1 | 1-D Collapsed Gallery | → `hall` |

---

## Endpoint Detection Changes

| Fixture | Phase 2 Endpoint | Phase 2 Endpoint Role | Endpoint Emphasized | Phase 2.5 Endpoint | Phase 2.5 Endpoint Role | Endpoint Emphasized |
|---|---|---|---|---|---|---|
| crucible_l1 | R4 | descent | Yes | R4 | descent | Yes |
| crucible_l2 | r06 | **unknown** | **No** | r06 | transition | Yes |
| crucible_l3 | **r7** (Prime Golem Lair) | boss | Yes | **r8** (Power Core Chamber) | objective | Yes |
| tomb_l1 | 1-E | descent | Yes | 1-E | descent | Yes |

The two key fixes:

- **Crucible L2**: `Maintenance Tunnel` was resolved as `unknown` by name inference, so it received no endpoint emphasis. Explicit `endpoint_room_id: r06` + `layout_role: transition` corrects both the role and the emphasis.
- **Crucible L3**: Name inference ranked `Prime Golem Lair` (boss) as the endpoint because boss outranked the rooms that followed. Explicit `endpoint_room_id: r8` correctly designates `Power Core Chamber` as the floor destination while `Prime Golem Lair` retains its `boss` role and high visual priority.

---

## Warning Changes

| Fixture | Phase 2 Warnings | Phase 2.5 Warnings |
|---|---|---|
| crucible_l1 | MISSING_OBJECTIVE_ROLE, MISSING_SEMANTIC_ROLE | MISSING_OBJECTIVE_ROLE |
| crucible_l2 | MISSING_OBJECTIVE_ROLE, MISSING_SEMANTIC_ROLE | MISSING_OBJECTIVE_ROLE |
| crucible_l3 | MISSING_ENTRANCE_ROLE, MISSING_SEMANTIC_ROLE | — |
| tomb_l1 | MISSING_OBJECTIVE_ROLE, MISSING_SEMANTIC_ROLE | — |

`MISSING_SEMANTIC_ROLE` (triggered when any room is `unknown`) is eliminated across all fixtures. `MISSING_ENTRANCE_ROLE` on Crucible L3 is eliminated because `r1 Control Nexus` now has an explicit `entrance` role. Two fixtures retain `MISSING_OBJECTIVE_ROLE` because their endpoint rooms are `descent`/`transition`, which are not counted as objective-type roles by the scorer — this is intentional and expected.

---

## Notable Visual Changes

### Crucible L2 — Maintenance Tunnel
Before: rendered as a low-priority `unknown` room; endpoint was detected but not emphasized because the endpoint role was `unknown`.
After: rendered as a `transition` room at medium visual priority; endpoint emphasis is applied — the floor destination reads clearly.

### Crucible L3 — Power Core Chamber vs Prime Golem Lair
Before: `Prime Golem Lair` (boss) was the auto-detected endpoint because boss priority outranked later rooms. `Power Core Chamber` was misclassified as `boss` by name inference and had no endpoint emphasis.
After: `Power Core Chamber` is explicitly the endpoint (`objective`) and receives endpoint emphasis. `Prime Golem Lair` remains a high-priority `boss` room. Both are visually distinct — the boss room reads as a major encounter on the path to the objective endpoint.

### Crucible L3 — Control Nexus
Before: `key_room` (name inference assigned it based on "control" keyword). No entrance role.
After: `entrance` (explicit). The floor now reads clearly as starting at Control Nexus.

### Tomb L1 — Drowned Shrine, Rat Warren, Collapsed Gallery
Before: all three rooms were `unknown` — they had no semantic identity and received the default low-priority unknown styling.
After: `objective`, `hazard`, `hall` respectively. Drowned Shrine now reads as a meaningful point of interest. Rat Warren reads as a danger/optional area. Collapsed Gallery reads as a connecting passage.

---

## Summary Assessment

Phase 2.5 successfully improved semantic accuracy across all four target fixtures without regressing geometry or layout quality. The largest improvement was Crucible L2 (+30.9 semantic score), where two unknown rooms and a non-emphasized endpoint were the primary drag. The endpoint override machinery resolved the core Phase 2 limitation identified in the spec: that boss-priority automatic detection could misidentify the floor endpoint when the true destination came later in the layout.
