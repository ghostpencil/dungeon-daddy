# Test Suite Assessment — full — 2026-05-23

**772 tests passing, 0 failing**

---

## Red Flags (fix immediately)

### [L4] OR-branch assertion — `tests/unit/ui/test_map_panel_zoom.py:154`

```python
px, py = panel.pan_offset
assert px != pytest.approx(0.0) or py != pytest.approx(0.0)
```

The test intends to verify that zoom-to-center adjusts the pan offset. With `or`, the assertion passes
if *either* coordinate is non-zero — meaning a broken implementation that adjusts only one axis (or
the wrong one) still passes. Zoom-to-center should produce a non-zero shift on both axes when zooming
from a centered viewport; the assertion should be `and`, not `or`, unless there is a documented case
where one axis stays at zero.

---

## Yellow Flags (address in next review)

### [L4 extended] Proxy assertions with no content check

- `tests/unit/llm/test_wizard_agent.py:118` — `assert len(provider.last_system) > 0` (phase=1 call).
  The phase=2 test at line 128 does check content (`"Lock & Key" in provider.last_system`). The phase=1
  test is the odd one out: it only verifies the system prompt is non-empty, not that it contains any
  dungeon-wizard–specific content. A system prompt of `" "` or the wrong prompt would pass.

- `tests/unit/llm/test_design_agent.py:103` — `assert len(provider.last_system) > 0`. The sibling
  test at line 110 (`test_build_context_includes_title`) does check real content via `_build_context`.
  But the system-prompt test itself stops at length. Should assert at least one distinctive phrase from
  the design-agent prompt (e.g., a keyword that distinguishes it from the wizard or DM agent).

### [L3] Two files over 500 lines

- `tests/unit/views/test_design_view.py` — 724 lines. Size is earned: it covers three `_run_*`
  methods, all queue-drain branches, error paths for each result type, thread launch, context-doc
  overlay state, overwrite-or-rename flow, Test Drive vs. Start Play routing, and direct field
  assertions (SI-3 section). No thinness concern.

- `tests/unit/data/test_models.py` — 522 lines. Also earned: covers round-trip, alias serialization,
  all six `validate_dungeon` rules, loop/room role fields, `auto_fix_dungeon`, and schema evolution.
  No thinness concern.

Both files are flagged for size only; behavior coverage is healthy.

### [L2 extended] `test_llm_integration.py` has happy paths only, and is fully skippable

All three `@_NEEDS_KEY` tests (`test_dm_agent_responds`, `test_wizard_agent_responds`,
`test_generator_agent_responds`) check only that a non-empty string is returned and doesn't start with
`"⚠"`. No test injects a provider failure or a malformed response to verify the error contract. Since
these are real-network tests that are skipped in CI, the error branch is entirely covered only by the
unit-level mocks in `test_dm_agent.py` / `test_wizard_agent.py` — which is the right place for it.
Low urgency, but worth noting.

---

## Green Signals Confirmed

- **Factory functions** — `_make_*` helpers appear at the top of every major test file and are reused
  across all tests in that file. No copy-paste setup.

- **Error paths paired with happy paths** — present throughout: `test_design_view.py` has error result
  tests for all three result types (chat, wizard, level); `test_dungeon_persistence.py` covers corrupt
  UTF-8 and missing files alongside the round-trip tests; `test_models.py` pairs each
  `validate_dungeon` success case with a failure case.

- **State assertions follow mock assertions** — most tests check both `mock.assert_called_*` *and*
  `assert view._field == value`. The SI-3 section of `test_design_view.py` and the full
  `test_play_view_threading.py` are good examples.

- **Integration tests use real filesystem** — `test_dungeon_persistence.py` and
  `test_validation_persistence.py` use `tmp_path` throughout; no mocked I/O.

- **Threading guards verified by real threads** — both `test_play_view_threading.py` and
  `test_design_view_threading.py` use `_SlowProvider` (real `time.sleep`) and join the thread,
  confirming `_llm_busy` is cleared without `on_update` intervention.

- **Routing validation has committed fixtures** — `tests/fixtures/tomb.json` and `crucible.json` are
  present; 102 routing tests run on every pass.

- **"No crash" named tests all assert real contracts** — every test with `_no_crash` or
  `_does_not_raise` in its name also asserts specific state (e.g., `cb.assert_not_called()`,
  `panel._active_variant == "Graph"`, `stepper._up_btn is None`). The names are mildly misleading but
  the bodies are sound.

---

## Summary

The suite is in strong shape: 772 tests, all green, with real-thread guards, real-filesystem
integration tests, committed routing fixtures, and consistent factory patterns. The single urgent fix
is the OR-branch in `test_map_panel_zoom.py:154` — it could silently pass a half-broken zoom
implementation. The two proxy `len > 0` assertions in the agent system-prompt tests are the most
meaningful yellow item: replacing them with a content check (one distinctive phrase from each agent's
prompt) would give the tests real discriminating power.
