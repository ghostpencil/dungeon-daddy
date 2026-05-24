# Test Suite Improvement Plan

## Summary of Findings

746 tests passing, 0 failures as of 2026-05-23. The suite has solid coverage of
the data, routing, and repository layers. Two systemic problems remain:

1. **Views are heavily mocked.** `test_design_view.py` and `test_play_view.py`
   verify that mocks were called with expected arguments rather than that data
   flows correctly. State mutations (`_llm_busy`, `_current_level`, chat history
   length) are undertested relative to call-count assertions.

2. **Error paths are missing.** LLM failures (timeouts, malformed JSON, conflicting
   data), corrupt file recovery, and thread guard logic have zero or near-zero
   test coverage. These are high-probability failures in real sessions.

This document captures the specific gaps and what to build to close them.

---

## Improvement Areas

---

### A — LLM Error Paths

**Problem:** No tests for what happens when the LLM call fails.
The architecture already defines the contract (`LLMResult(error=...)` →
`⚠ The dungeon is silent. ({error})`) but it is untested.

**Risk:** Failures in play mode are silent or produce incorrect UI state.

**Tests to add — `tests/unit/views/test_play_view.py`**

```
test_dm_error_result_shows_canonical_error_bubble
  - put DMResult(content="", error="API timeout") in queue
  - call on_update(0)
  - assert _chat.add_message called with ("system", "⚠ The dungeon is silent. (API timeout)")
  - assert _llm_busy is False

test_dm_error_result_clears_busy_flag
  - put DMResult(content="", error="any error") in queue
  - view._llm_busy = True before on_update(0)
  - assert _llm_busy is False after on_update(0)
```

**Tests to add — `tests/unit/views/test_design_view.py`**

```
test_chat_error_result_shows_error_bubble
  - put LLMResult(content="", error="rate limit", result_type="chat") in queue
  - call on_update(0)
  - assert _chat.add_message called with ("system", expected error string)
  - assert _llm_busy is False

test_wizard_error_result_shows_error_bubble
  - same pattern for result_type="wizard"

test_level_error_result_shows_error_bubble
  - same pattern for result_type="level"
```

**Tests to add — `tests/unit/llm/test_dm_agent.py`**

```
test_dm_respond_propagates_llm_error
  - provider.complete raises LLMError("connection refused")
  - assert agent.respond() raises LLMError (not swallowed)
  - confirms caller (the view thread) is responsible for catching and queuing
```

---

### B — View Tests: State Mutations Over Call Counts

**Problem:** Most view assertions are `mock.assert_called_once_with(...)`. When the
view logic changes (different call site, different call order), the test may still
pass even if the actual state is wrong. State mutation tests are harder to fool.

**What to do:** For each behavior that changes view state, assert the state
directly instead of (or in addition to) the mock call.

**High-value state to assert:**

| State field | Currently tested? | What to add |
|---|---|---|
| `view._llm_busy` | Yes (some tests) | Cover all paths that set/clear it |
| `view._chat_history` length | Rarely | After send: +1; after DM response: +1 |
| `view._current_level` | Not via state | After `level` result: incremented |
| `view._generation_retries` | Not via state | After validation failure: incremented |
| `view._brief` | Partially | After wizard result: populated |

**Tests to add — `tests/unit/views/test_play_view.py`**

```
test_on_send_appends_to_chat_history
  - view._chat_history = []
  - call view.on_send("hello from GM")
  - assert len(view._chat_history) == 1
  - assert view._chat_history[0].role == "gm"
  - assert view._chat_history[0].content == "hello from GM"

test_on_send_sets_llm_busy
  - view._llm_busy = False
  - call view.on_send("hello")
  - assert view._llm_busy is True

test_on_send_while_busy_does_nothing
  - view._llm_busy = True
  - view._chat_history = []
  - call view.on_send("hello")
  - assert len(view._chat_history) == 0  # dropped, not appended

test_dm_result_appends_to_chat_history
  - view._chat_history = []
  - put DMResult(content="You see a door.") in queue
  - call on_update(0)
  - assert len(view._chat_history) == 1
  - assert view._chat_history[0].role == "dm"
```

**Tests to add — `tests/unit/views/test_design_view.py`**

```
test_level_result_increments_current_level
  - view._current_level = 1
  - put valid level JSON result in queue (result_type="level")
  - call on_update(0)
  - assert view._current_level == 2

test_wizard_result_populates_brief
  - view._brief = None
  - put LLMResult(content=serialized_brief, result_type="wizard") in queue
  - call on_update(0)
  - assert view._brief is not None
  - assert view._brief.title == expected_title

test_generation_retry_increments_on_invalid_level
  - view._generation_retries = 0
  - put LLMResult with invalid level JSON (fails validation) in queue
  - call on_update(0)
  - assert view._generation_retries == 1
```

---

### C — Thread Lifecycle (Double-Send Guard)

**Problem:** The `_llm_busy` guard prevents a second LLM call while one is in
flight, but only via mock — no test uses a real thread. If the guard logic is
accidentally removed or bypassed, no test will catch it.

**What to do:** One integration-style test using a real provider mock that blocks
briefly, confirming the guard works with real threads.

**Tests to add — `tests/unit/views/test_play_view_threading.py` (new)**

```
test_second_send_while_thread_running_is_dropped
  - Create a provider mock whose complete() blocks for 100ms
  - Inject real provider (not MagicMock agent) into view
  - Call on_send("first message") — thread spawns, view._llm_busy = True
  - Immediately call on_send("second message") — should be dropped
  - Join the thread
  - Assert only one LLM call was made (provider.complete called once)
  - Assert view._chat_history has exactly one GM message

test_busy_flag_cleared_after_thread_completes
  - Provider mock returns immediately
  - Call on_send("hello")
  - Join the active thread
  - Assert view._llm_busy is False (not relying on on_update to clear it)
  Note: clearing happens in the thread itself (finally: self._llm_busy = False)
  not in on_update — this test confirms that contract.
```

**Note on scope:** Do not test thread timing or race conditions on the queue.
The architecture uses `queue.Queue` which is thread-safe by design.
Test the guard contract, not the underlying queue mechanism.

---

### D — Generator Output: Conflicting and Malformed Data

**Problem:** `test_generator_agent.py` tests null→role coercion but not:
- Conflicting loop roles in the generated JSON (two rooms both claim "main_exit")
- Generator returning content that passes JSON parsing but fails Pydantic validation

**Risk:** Invalid dungeon levels are silently accepted or produce confusing errors.

**Tests to add — `tests/unit/llm/test_generator_agent.py`**

```
test_generate_level_with_conflicting_main_exit_roles_raises_or_demotes
  - Build a level JSON where two rooms have role="main_exit"
  - Confirm agent either raises a descriptive error OR demotes the second
    occurrence to role=null (whichever matches implementation)
  - Document the contract clearly in the test name

test_generate_level_json_fails_pydantic_validation_returns_error_string
  - Provider returns valid JSON that fails Pydantic (e.g. missing required field)
  - Assert agent surfaces the error via its return/raise contract
  - Do not assert a specific error string — assert error is not None / is raised
```

**Also fix — `tests/unit/llm/test_generator_agent.py`**

```
Existing weak assertion at line ~322:
  assert "none" in ctx.lower() or "no error" in ctx.lower() or "0" in ctx

Replace with a specific assertion for whichever string the implementation
actually produces. If all three are valid, document why with a comment.
```

---

### E — Memory File Corruption Recovery

**Problem:** `test_view_transition.py` line 102 tests that a corrupt session JSON
does not crash — but only checks "no crash." There is no test for:
- Partial memory markdown (truncated mid-write)
- Memory file with invalid UTF-8
- Repository returning an error-scoped result vs. empty string

**Risk:** Corrupt memory silently produces empty context for the DM agent,
or crashes play mode mid-session.

**Tests to add — `tests/integration/test_dungeon_persistence.py` (extend)**

```
test_load_room_memory_returns_empty_string_for_truncated_file
  - Write a memory file that is cut off mid-line (simulate partial write)
  - Call repo.load_room_memory(dungeon_id, level_id)
  - Assert result is a non-empty string OR empty string — not an exception
  - The key contract: load_room_memory() never raises, always returns str

test_load_room_memory_returns_empty_string_for_missing_file
  - Call repo.load_room_memory() for a dungeon with no memory dir
  - Assert result == ""
  - (May already pass — confirm and document explicitly)
```

**Tests to add — `tests/unit/views/test_play_view.py`**

```
test_on_room_click_with_empty_memory_still_calls_agent
  - repo.load_room_memory returns ""
  - Call view.on_room_click(room_id)
  - Assert DM agent thread is spawned (view._llm_busy is True)
  - Confirm empty memory string does not block the call
```

---

### F — Assertion Quality

**Problem:** Several tests have OR-branch assertions that allow almost any output to
pass, or assertions that proxy the real contract (char count instead of token count).

**Fixes — audit and tighten**

```
tests/unit/llm/test_generator_agent.py ~line 322
  Replace three-way OR with the single string the implementation produces.
  If multiple strings are valid, add an explicit comment: "# valid_formats = [...]"

tests/unit/llm/test_context_builder.py ~line 121
  The assertion `assert "\n\n\n" not in result` checks whitespace but not compaction.
  Add: assert len(result) < len(original_input) to confirm compaction occurred.
  Do not assert exact token counts — char reduction is a fair proxy.

tests/unit/views/test_play_view.py ~line 234
  Replace `"room-a" in m and "room-b" in m` with a check that both IDs
  appear in the same message, or document why split-message is acceptable.
```

---

### G — Routing Validation: Local Edge Cases

**Problem:** `test_routing_validation.py` skips all parametrized tests if the
`fixtures/` directory is absent, silently turning the suite into a no-op in
clean checkouts.

**Tests to add — `tests/unit/map/test_routing.py` (extend, not new file)**

```
test_routing_single_room_level_returns_empty_connections
  - Level with one room, zero connections
  - Routing should complete without error and return nothing to draw

test_routing_adjacent_rooms_no_detour_needed
  - Two rooms sharing an edge (gap = 0 between them)
  - Assert path is direct, not a detour

test_routing_room_at_grid_boundary
  - Room placed at x=0, y=0 (minimum coordinates)
  - Assert no IndexError or negative-coordinate path segment
```

These run unconditionally and do not depend on external fixture files.

---

## Out of Scope

The following are acknowledged gaps but are not worth addressing now:

- **Concurrent file writes** — `append_room_event()` is called sequentially; no
  threading around file I/O in the current architecture.
- **Token budget accuracy** — testing real tokenization requires the provider SDK
  in unit tests. The char-count proxy is a pragmatic trade-off.
- **Full UI state machine** — WIZARD → EDIT → LEVEL_WIZARD permutations. These
  are covered by smoke tests; unit tests cover the dispatch logic only.
- **LLM API rate limits and retries** — the provider layer handles these; agent
  tests should not test provider internals.

---

## Implementation Order — First Audit (SI-1 through SI-7) — COMPLETE

| SI | Area | Files | Status |
|---|---|---|---|
| SI-1 | A — LLM error paths | `test_play_view.py`, `test_design_view.py`, `test_dm_agent.py` | DONE |
| SI-2 | F — Fix weak assertions | `test_generator_agent.py`, `test_context_builder.py`, `test_play_view.py` | DONE |
| SI-3 | B — View state mutations | `test_play_view.py`, `test_design_view.py` | DONE |
| SI-4 | E — Memory corruption | `test_dungeon_persistence.py`, `test_play_view.py` | DONE |
| SI-5 | D — Generator conflicts | `test_generator_agent.py` | DONE |
| SI-6 | G — Routing edge cases | `test_routing.py` | DONE |
| SI-7 | C — Thread lifecycle | `test_play_view_threading.py` (new) | DONE |

769 tests passing after SI-7.

---

## Second Audit — 2026-05-23

Second `/assess-tests` pass run against the 769-test suite.
Full report: `spec/TEST_SUITE_ASSESSMENT_20260523.md`.

Four new red flags and one yellow gap elevated to tracked items.

---

### H — OR-branch assertions in generator agent (SI-8)

**Problem:** Four assertions in `tests/unit/llm/test_generator_agent.py` use
multi-way OR against a fixed constant (`SYSTEM_PROMPT`) and a deterministic
function (`_build_context()`). The expected string is knowable — OR is masking
that the developer was uncertain what the code produced.

```
line 431: assert "1 empty cell" in prompt or "gap" in prompt.lower()
line 439: assert "right edge" in prompt.lower() or ("x≥" in prompt or "x >=" in prompt)
line 463: assert '"main"' in ctx or "type=main" in ctx or "main loop" in ctx.lower()
line 464: assert '"sub"' in ctx or "type=sub" in ctx or "sub-loop" in ctx.lower() or "sub loop" in ctx.lower()
```

**Fix:** Run the code, observe the actual substrings, pin each to one exact string.
If the implementation is intentionally flexible, document exactly which variants
are valid with an inline comment.

---

### I — No-crash tests missing contract assertions (SI-9)

**Problem:** Four tests are named `*_no_crash` or `*_does_not_raise` and have no
assertion beyond implicit "no exception raised":

| File | Line | Test | Missing assertion |
|---|---|---|---|
| `test_design_view.py` | 548 | `test_on_hide_view_no_crash_without_active_thread` | `_active_thread` still None, `_llm_busy` unchanged |
| `test_level_stepper.py` | 100 | `test_set_up_enabled_before_setup_does_not_raise` | widget internal state unchanged |
| `test_level_stepper.py` | 103 | `test_set_down_enabled_before_setup_does_not_raise` | widget internal state unchanged |
| `test_map_panel_zoom.py` | 169 | `test_variant_tab_click_no_callback_does_not_raise` | `_active_variant` unchanged, buttons not updated |

**Fix:** Add at least one state assertion to each. The recovery contract belongs
in the test, not just its name.

---

### J — Routing validation module fully skippable (SI-10)

**Problem:** `tests/unit/map/test_routing_validation.py` computes `_PARAMS` from
`tests/fixtures/` at import time. No fixture files are committed, so the entire
module is skipped via `pytest.skip(allow_module_level=True)`. The routing
correctness contract (detour waypoints stay within local bounding region) has
zero test coverage in a clean checkout.

**Fix:** Commit at least one dungeon JSON to `tests/fixtures/` so `_PARAMS` is
non-empty and the parametrized tests run. A minimal two-room dungeon is sufficient.

**Note:** SI-6 added unconditional routing tests to `test_routing.py`. Those cover
edge cases. SI-10 ensures the fixture-driven validation tests also execute.

---

### K — DesignView threading guard never tested with real threads (SI-11)

**Problem:** `test_design_view.py` patches `threading.Thread` in every test. The
`_llm_busy` guard for DesignView has three thread-launching paths (wizard,
level-wizard, design chat) and none are exercised with a real thread. Removing
the guard would not cause any test to fail.

PlayView already has `test_play_view_threading.py` with a `_SlowProvider` stub
pattern. DesignView needs the same.

**Tests to add — `tests/unit/views/test_design_view_threading.py` (new)**

```
test_design_view_busy_flag_cleared_after_wizard_thread_completes
  - _SlowProvider blocks 100ms then returns a fixed brief JSON string
  - call view._on_chat_send("hello") in wizard mode
  - join view._active_thread
  - assert view._llm_busy is False

test_design_view_second_wizard_send_dropped_while_busy
  - _SlowProvider blocks 100ms
  - first _on_chat_send spawns thread, _llm_busy = True
  - second _on_chat_send immediately → dropped
  - join thread
  - assert provider.complete called exactly once
```

Cover at least wizard mode. Level-wizard and design-chat paths can follow if
the guard implementation differs.

---

### L — Proxy assertions in LLM integration tests (SI-12)

**Problem:** `tests/integration/test_llm_integration.py` lines 61, 71, 91 each
end with:

```python
assert isinstance(result, str)
assert len(result) > 0
```

These pass if the API returns a single space. There is no check that the response
is plausible prose (no `"⚠"` prefix, at least one whitespace-delimited word longer
than 2 characters, etc.).

**Fix:** Add a minimum plausibility check after `len(result) > 0`:

```python
assert not result.startswith("⚠")          # not an error string
assert any(len(w) > 2 for w in result.split())  # contains real words
```

These are yellow-flag fixes — apply when running the integration suite with a
real key. Do not require a key for the fix itself.

---

## Implementation Order — Second Audit (SI-8 through SI-12)

| SI | Area | Files | Effort | Priority |
|---|---|---|---|---|
| SI-8 | H — OR-branch assertions | `test_generator_agent.py` | Small | 1 — red flag |
| SI-9 | I — No-crash contract assertions | `test_design_view.py`, `test_level_stepper.py`, `test_map_panel_zoom.py` | Small | 2 — red flag |
| SI-10 | J — Routing fixture | `tests/fixtures/` (new JSON) | Small | 3 — red flag |
| SI-11 | K — DesignView real-thread guard | `test_design_view_threading.py` (new) | Medium | 4 — yellow |
| SI-12 | L — Integration proxy assertions | `test_llm_integration.py` | Small | 5 — yellow |

Work red flags first (SI-8, SI-9, SI-10). Use TDD skill before creating SI-11.

---

## TDD Protocol

Follow the standard red-green-refactor loop for each item. When adding tests to
an existing file, open that file first and check for existing fixtures or
factories to reuse. Do not write a new `_make_view()` factory if one exists.

Use the TDD skill before writing any new test file (SI-11 — `test_design_view_threading.py`).
For additions to existing files, the TDD skill is not required.

---

## Lessons Learned

This section records the patterns of weakness found in this audit and the best
practices that follow from them. The intent is to codify these as standing
guidance — and eventually as a reusable test suite assessment skill.

---

### Lesson 1 — Mock call counts are not behavior contracts

**Finding:** The view tests (`test_design_view.py`, `test_play_view.py`) heavily
use `mock.assert_called_once_with(...)`. A test that asserts a mock was called does
not verify what the code *did* — only that it *delegated*. When mock boundaries
change (renamed method, different call site), the test breaks without exposing a
real bug, or passes without detecting a real regression.

**Best practice:** Assert state, not delegation.
- After an action, check the view's own fields: `_llm_busy`, `_chat_history`,
  `_current_level`, `_brief`.
- Reserve `assert_called_once_with` for cross-boundary contracts that are
  genuinely opaque (e.g. confirming the repo was told to save, not how it saved).
- A useful test can do both: assert state changed AND the right collaborator was called.

**Smell to watch for:** A test file where every assertion is `mock.assert_*` and
no field values are checked after the action.

---

### Lesson 2 — Error paths are first-class behaviors

**Finding:** The threading model has a clearly defined error contract in
`ARCHITECTURE.md` (`LLMResult(error=...)` → canonical error bubble), but zero
tests verified it. Error paths written during initial build tend to be optimistic
— they handle the happy path and leave error handling as "obviously correct" code
that accumulates subtle bugs over time.

**Best practice:** For every async operation that can fail, write at least one
test that injects a failure and asserts the canonical error response.
- If the architecture documents a specific error format, that format is a contract —
  test it explicitly.
- Inject failures at the provider boundary, not deep inside implementation internals.
- The test should confirm both the visible output (error message in chat) and the
  state cleanup (`_llm_busy` cleared, thread reference dropped).

**Smell to watch for:** An architecture doc that defines an error format with no
corresponding test asserting that format.

---

### Lesson 3 — Large test files with thin coverage are a trap

**Finding:** `test_design_view.py` is 907 lines. Despite its size, it misses
meaningful state-mutation tests and all error paths. File size creates an
illusion of thoroughness.

**Best practice:** Evaluate coverage by behavior surface, not line count.
- Ask: "What are the distinct outcomes this module can produce?" Each distinct
  outcome needs at least one test.
- A 900-line test file that tests one path through ten behaviors is weaker than
  a 200-line file that tests two paths (happy + error) through five behaviors.
- During review, count distinct outcome assertions, not test count.

**Smell to watch for:** A test file whose size has grown significantly without a
corresponding increase in the number of distinct behaviors covered.

---

### Lesson 4 — OR-branch assertions are untestable specifications

**Finding:** `test_generator_agent.py` line ~322 had:
```python
assert "none" in ctx.lower() or "no error" in ctx.lower() or "0" in ctx
```
This passes for almost any string. It does not test a contract — it documents
uncertainty about what the implementation actually produces.

**Best practice:** An assertion with OR branches means the expected output is
unknown. Before writing the assertion, run the code and observe the actual output.
Then assert that exact output.
- If multiple outputs are legitimately valid, document them explicitly with a
  comment: `# valid when provider returns X or when schema is Y`.
- Never use an OR-branch assertion to make a failing test pass without
  understanding why it was failing.

**Smell to watch for:** `assert a or b or c` in a test body. Always investigate
and collapse to a single expected value.

---

### Lesson 5 — Skippable test groups must have unconditional fallbacks

**Finding:** `test_routing_validation.py` uses `pytest.skip` when the `fixtures/`
directory is absent. In a clean checkout, the entire parametrized suite silently
becomes a no-op. `pytest` reports "0 failed, N skipped" which reads as healthy.

**Best practice:** External-fixture tests must be paired with unconditional local
tests that cover edge cases without requiring the external data.
- Parametrize against external fixtures for realistic coverage.
- Add at least 2–3 unconditional tests using inline-constructed inputs for edge
  cases (empty input, boundary values, minimum valid case).
- The unconditional tests ensure the module is not completely uncovered in clean
  environments.

**Smell to watch for:** A test file where all test cases are inside a parametrize
block whose parameters come from a directory or external source.

---

### Lesson 6 — Integration tests must assert contracts, not just absence of crashes

**Finding:** `test_view_transition.py` line 102 confirmed corrupt session JSON
does not crash — but did not assert what the application actually does with a
corrupt file (creates fresh state, logs a warning, etc.).

**Best practice:** "Does not raise" is necessary but not sufficient. Every
error-recovery test should also assert the recovery behavior:
- What state is the system in after recovery?
- Is stale data discarded cleanly?
- Is the user informed (error message, default state)?

The recovery contract belongs in the test name:
`test_corrupt_session_json_starts_fresh_state` is more useful than
`test_corrupt_session_json_no_crash`.

**Smell to watch for:** A test whose only assertion is `with pytest.raises(...)` or
a try/except with no assertion in the except block, or a test named `*_no_crash`.

---

### Lesson 7 — Test the threading contract, not the thread implementation

**Finding:** All threading in the view layer was tested by mocking the thread
entirely. The double-send guard (`_llm_busy`) was verified only against mocks,
meaning a refactor that removes the guard would not be caught.

**Best practice:** Write at least one integration-style test that spawns a real
(short-lived) thread and confirms the guard contract holds with real concurrency.
- Use a provider mock that blocks briefly (e.g. `time.sleep(0.05)`) to create a
  window where a second send can be attempted.
- Keep the test deterministic: join the thread before asserting.
- This is not a stress test — one scenario is enough to confirm the contract is real.

**Smell to watch for:** A threading guard that is only exercised through mocked
collaborators. If removing the guard would not cause any test to fail, the guard
is untested.

---

### Assessment Checklist

When evaluating a test suite, check for each of these signals:

**Red flags (fix immediately):**
- [ ] Defined error format in architecture docs with no test asserting that format
- [ ] `assert a or b or c` anywhere in a test body
- [ ] All assertions in a test file are `mock.assert_*` with no state checks
- [ ] Test named `*_no_crash` with no assertion about post-crash state
- [ ] Parametrized test group that is entirely skipped in a clean checkout

**Yellow flags (address in next suite review):**
- [ ] Test file > 500 lines with no error-path tests
- [ ] Threading guard tested only through mocked collaborators
- [ ] Integration test that uses `tmp_path` but only tests the happy path
- [ ] LLM agent test that has no test for malformed provider output
- [ ] `assert len(result) > 0` with no assertion about what the result contains

**Green signals (patterns to maintain):**
- [ ] Each distinct module outcome has at least one test
- [ ] Error paths paired with their corresponding happy path tests
- [ ] Factory functions at top of test file reused across all tests in that file
- [ ] State assertions follow mock call assertions (both present)
- [ ] Integration tests use real filesystem (`tmp_path`), not mocked I/O
