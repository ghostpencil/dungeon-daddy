# Test Suite Cleanup — Deletion / Merge Candidates

**Status:** APPLIED. The deletions and merges below have been applied to the test
files; full suite green at **2424 passed**. This document is retained as the
rationale record for what was removed/consolidated.

**Suite size at time of review:** ~2,260 test functions across 177 files
(93% unit, 7% integration, <1% evals).

**Aggressiveness:** Moderate — clear-cut duplicates, stale tests, tautological
constant/default tests, the weakest field-assignment tests, plus consolidation of
parametrizable groups. Coverage must be preserved.

## Criteria

1. Extremely low value (impossible/near-impossible conditions, or framework behavior)
2. Stale/invalid (feature changed significantly or removed)
3. Over-mocked to the point of always passing
4. Duplicate of another test
5. Closely related to another test; mergeable without losing value

## Important caveat applied during review

`spec/TESTING.md` **mandates** mocking Arcade rendering (`arcade.draw_*`) and the
LLM API — there is no GPU or network in the test environment. Therefore:

- Tests that mock Arcade and assert on draw-call arguments are the **sanctioned
  pattern**, not C3 violations, *when they assert real geometry/color/layout logic*.
- Provider tests that mock `anthropic.Anthropic` to verify **error translation,
  kwarg passing, or response parsing** test the only logic the adapter has.

These were reviewed and are **kept** (see "Reviewed but keeping" below). Every
candidate below was confirmed by reading the actual test, not taken on trust.

---

## Summary

| Criterion | Action | Count |
|---|---|---|
| C1 — trivial/low-value | DELETE | ~12 |
| C2 — stale/invalid | — | 0 (none found) |
| C3 — over-mocked/tautological | DELETE | 0 (all reviewed → keep) |
| C4 — duplicate | MERGE/DELETE | folded into C5 below |
| C5 — mergeable groups | MERGE → parametrize | ~24 tests → ~5 |
| **Net function reduction (estimate)** | | **~30–35** |

---

## C1 — Trivial / low-value (recommend DELETE)

These assert only that Pydantic stores a passed value or applies a declared
default — i.e. they test the framework, not project logic. In each case the model
is already *constructed and exercised* by a sibling test that checks real behavior
(round-trip, validation, or computed property), so deleting these loses no coverage.

| File | Test | Why | Note |
|---|---|---|---|
| `tests/unit/data/test_models.py` | `test_loop_new_fields_have_defaults` | asserts `loop.type=="main"`, `explanation==""`, `rooms==[]` | logic covered by `test_loop_type_accepts_sub` / `_rejects_invalid` / `_explanation_and_rooms_accept_values` |
| `tests/unit/data/test_models.py` | `test_room_new_fields_default_to_none` | asserts two fields default to `None` | construction covered by `test_room_sub_loop_roles_accepts_list_of_dicts` |
| `tests/unit/data/test_models.py` | `test_room_main_loop_role_accepts_string` | pure field assignment | trivial; sibling list-of-dicts test exercises the real conversion |
| `tests/unit/data/test_models.py` | `test_validation_result_warnings_defaults_to_empty` | asserts `warnings==[]` default | logic covered by `test_validation_result_warnings_do_not_affect_is_valid` (tests `__bool__`) |
| `tests/unit/data/test_models.py` | `test_dungeon_meta_save_name_defaults_to_none` | asserts one field defaults to `None` | covered by `test_dungeon_meta_save_name_round_trips` |
| `tests/unit/rpg/test_models.py` | `TestReactionClockLine::test_constructs_with_required_fields` | field assignment only | construction exercised by `TestWorldReaction::test_holds_clock_and_stress_lines` |
| `tests/unit/rpg/test_models.py` | `TestReactionStressLine::test_constructs_with_required_fields` | field assignment + default | same; construction exercised by the WorldReaction test |
| `tests/unit/rpg/test_models.py` | `TestActorState::test_status_defaults_to_active` | **also C4** — duplicates the `status=="active"` assertion already inside `TestActorState::test_constructs_with_required_fields` (line 112) | pure duplicate |
| `tests/unit/rpg/test_models.py` | `TestActorState::test_actions_defaults_to_empty_dict` | asserts `actions=={}` default | trivial default |
| `tests/unit/map/layout/test_models.py` | `TestPort::test_construction` | field assignment only | construction covered by `TestPort::test_valid_sides` |
| `tests/unit/map/layout/test_models.py` | `TestRoutedEdge::test_construction` | field assignment + `len(points)==3` | construction covered by `test_bend_count_*` |
| `tests/unit/map/layout/test_models.py` | `TestRoutedEdge::test_warnings_default_empty` | asserts `warnings==[]` default | trivial default |

**Optional (judgment call, listed but defaulting to KEEP):**

- `tests/unit/data/test_models.py::test_design_mode_values` — looks tautological
  (`DesignMode.WIZARD == "wizard"`) but actually pins the **serialized wire format**
  of a `str` enum persisted to save files. Recommend **KEEP** as a contract guard.
- `tests/unit/rpg/test_models.py::TestReactionStressLine::test_triggered_fallout_can_be_set`
  pairs with the default-`False` assertion in the construct test. If the construct
  test is deleted, keep this one (it's the only place the `True` path is checked).

---

## C2 — Stale / invalid

**None found.** Grep for `@pytest.mark.skip` / `@pytest.mark.xfail` across `tests/`
returned no matches. Spot-checked imports resolve to existing modules. The
Phase 43–45 actor→faction split is covered by both `ActorManifest` and
`FactionManifest` variants; no orphaned tests for removed classes.

---

## C3 — Over-mocked / tautological

**No deletions recommended.** Candidates surfaced by exploration were reviewed and
rejected as deletion targets — see "Reviewed but keeping". The provider tests and
Arcade-render geometry tests verify real adapter/geometry logic under the
project's mandatory-mock policy.

---

## C5 — Mergeable groups (recommend MERGE → `@pytest.mark.parametrize`)

These preserve every input/assertion case while collapsing repetitive function
bodies. C4 duplicate pairs are folded in here as parametrization.

### 1. `tests/unit/rpg/test_actor_control.py::TestIsPlayerControlled` — 6 → 1
Six one-line tests differing only by actor type. Merge to:
```python
@pytest.mark.parametrize("actor_type,expected", [
    ("pc", True), ("npc", False), ("monster", False),
    ("dungeon", False), ("faction", False), ("dungeon_presence", False),
])
def test_is_player_controlled(actor_type, expected):
    assert is_player_controlled(actor_type) is expected
```

### 2. `tests/unit/ui/test_campaign_view.py` — the `*_sets_dirty` family — 12 → 1
All do: load manifest → call one mutator → assert `view.is_dirty is True`.
Affected: `test_add_actor_sets_dirty`, `test_update_actor_sets_dirty`,
`test_remove_actor_sets_dirty`, `test_set_player_side_sets_dirty`,
`test_add_clock_sets_dirty`, `test_update_clock_sets_dirty`,
`test_remove_clock_sets_dirty`, `test_add_memory_seed_sets_dirty`,
`test_remove_memory_seed_sets_dirty`, `test_add_room_threat_sets_dirty`,
`test_remove_room_threat_sets_dirty`, `test_attach_dungeon_sets_dirty` (~line 607).
Merge to one parametrized test taking a `(setup, mutation)` callable per case.

### 3. `tests/unit/ui/test_campaign_view.py` — actor/faction CRUD pairs (C4) — 4 → 2
Same code path, different collection:
- `test_update_actor_patches_field_in_world_actors` + `..._in_factions`
- `test_remove_actor_removes_from_world_actors` + `..._from_factions`
Merge each pair into one test parametrized by `(actor_factory, collection_name)`.

### 4. `tests/unit/map/layout/test_endpoint_emphasis.py` — single-role detection — 2(+1) → 1
`test_boss_room_detected_as_endpoint` and `test_objective_room_detected_as_endpoint`
differ only by the `role` string and can fold into the existing
`test_exit_family_detected_as_endpoint` parametrization (extend the role list to
include `"boss"`, `"objective"`). Keep the boss-only extra assertion
(`"AMBIGUOUS_ENDPOINT_ROLE" not in warnings`) as a separate one-liner if desired.

> The append/remove collection tests (`test_add_*_appends_*`, `test_remove_*_removes_*`)
> were considered for merging but each asserts a *different* manifest collection and
> membership semantic; merging them adds indirection for little gain. Recommend
> **leave as-is**.

---

## Reviewed but keeping (explicit false-positives)

These were flagged by automated exploration but should **NOT** be deleted:

| File | Test(s) | Why keep |
|---|---|---|
| `tests/unit/map/test_graph_renderer.py` | `test_connection_line_starts/ends_at_*_circle_edge`, `test_room_label_*` | Verify **real geometry math** (circle-edge offset via `math.hypot`) and label colors under the mandatory Arcade mock. Sanctioned pattern. |
| `tests/unit/map/test_graph_renderer.py` | `test_connection_line_does_not_start_at_room_center` | Regression guard; minor overlap with the edge-offset test but cheap and intentional. Optional fold-in only. |
| `tests/unit/llm/test_provider.py` | `test_anthropic_provider_raises_llm_error_not_api_error`, `test_anthropic_provider_does_not_leak_api_error` | Test real **error-translation** logic (the adapter's main job). High value. |
| `tests/unit/llm/test_provider.py` | `test_anthropic_provider_complete_passes_system_prompt`, `..._accepts_response_format_without_error`, `..._stream_yields_chunks` | Verify real kwarg-passing / parsing / streaming-join logic, not just mock returns. |
| `tests/unit/rpg/test_clocks.py` | `test_create_clock_defaults` | Tests the `create_clock` **factory** (sets `filled=0`, `status="active"`), not raw field storage. |
| `tests/unit/map/layout/test_models.py` | `RoomRect::test_edge_properties`, `test_center_properties`, `test_inflate_*`, `test_contains_point_*` | Test **computed properties / methods** (`right=x+w`, `cx`, `inflate`, `contains_point`), real logic. |
| `tests/unit/map/layout/test_models.py` | `LabelBox::test_construction` | Despite the name, asserts computed `right`/`top`; it is the only coverage of those. |
| `tests/unit/rpg/test_models.py` | `test_all_actor_types_accepted`, `test_all_statuses_accepted`, `test_invalid_*_rejected` | Validate the `Literal` union accepts/rejects the correct members — real validation behavior. |

---

## Next step (separate, after approval)

Apply the approved `DELETE` / `MERGE` actions to the test files, then run
`pytest -q` to confirm the suite stays green and the function count drops by the
estimated ~30–35.
