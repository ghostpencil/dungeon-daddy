# Test Suite Assessment

Assess the Dungeon Daddy test suite for quality signals using the 7 lessons
learned from the 2026-05-23 audit. Report findings in the conversation — do
not write files unless the user asks after seeing the report.

---

## Usage

`/assess-tests [scope]`

**Examples**
- `/assess-tests` — full suite
- `/assess-tests views` — scope to `tests/unit/views/`
- `/assess-tests llm` — scope to `tests/unit/llm/`
- `/assess-tests map` — scope to `tests/unit/map/`
- `/assess-tests integration` — scope to `tests/integration/`

---

## Workflow

### Step 1 — Resolve scope

Map the optional argument to a path:

| Argument | Path |
|---|---|
| (none) | `tests/` |
| `views` | `tests/unit/views/` |
| `llm` | `tests/unit/llm/` |
| `map` | `tests/unit/map/` |
| `integration` | `tests/integration/` |
| `unit` | `tests/unit/` |

Any other argument: treat as a path suffix under `tests/`.

### Step 2 — Run pytest

```
python -m pytest --tb=no -q <scope_path>
```

Record the pass/fail count. If tests are failing, note it at the top of the
report — findings are less meaningful against a broken suite.

### Step 3 — Collect test files

List all `test_*.py` files in scope. Note each file's line count. Files over
500 lines warrant extra scrutiny (Lesson 3).

### Step 4 — Apply the checklist

Read each file and check for the signals below. Read in sections for large
files — focus on assertion patterns, not setup code.

---

#### Red Flags — fix immediately

**[L4] OR-branch assertions**
Grep for `assert.*\bor\b` in test bodies. Each hit means the expected output
is unknown — the assertion passes on almost any input. Report file + line.

```python
# example smell
assert "none" in ctx.lower() or "no error" in ctx.lower() or "0" in ctx
```

**[L1] All assertions are mock.assert_* with no state checks**
Count `mock.assert_` calls vs. direct field assertions (`assert view._`,
`assert result.`, `assert len(`). Flag files where every assertion is a mock
call count and no internal state is checked after an action.

**[L2] Defined error contract with no test asserting it**
Look for modules with documented error formats (in ARCHITECTURE.md, docstrings,
or the format string `"⚠ The dungeon is silent."`). Check that at least one
test injects a failure and asserts the exact error output, plus state cleanup
(`_llm_busy`, thread reference).

**[L6] "No crash" tests with no contract assertion**
Search for test names matching `*_no_crash`, `*_no_error`, `*_does_not_raise`,
or tests whose only assertion is inside a `try/except` with no `assert` in the
`except` block. Each must also assert the recovery state.

**[L5] Fully-skippable parametrized groups**
Look for `pytest.skip` or `pytest.mark.skipif` wrapping an entire parametrize
block where the parameters come from an external directory or file. Flag if no
unconditional tests for the same module exist.

---

#### Yellow Flags — address in next review

**[L3] Large file, thin behavior coverage**
Flag any test file > 500 lines. Ask: how many *distinct outcomes* does the
module produce? Is each outcome (happy path + at least one error path) covered?
File size without outcome coverage is a trap.

**[L7] Threading guard tested only through mocks**
Look for guards like `_llm_busy`, `_active_thread`. Check whether any test
spawns a real (non-mocked) thread to verify the guard holds under real
concurrency. If the guard is only exercised through `MagicMock`, flag it.

**[L2 extended] Integration tests with happy path only**
Look for tests using `tmp_path` that have no sibling test for the error or
corruption path (truncated file, missing file, invalid UTF-8).

**[L4 extended] Proxy / under-specified assertions**
Look for `assert len(result) > 0` with no follow-up assertion about what the
result actually contains.

---

#### Green Signals — patterns to maintain

Confirm which of these are present and note them in the report:

- Factory functions (`_make_*`) at top of file, reused across all tests
- Error paths paired with happy path tests in the same file
- State assertions follow mock call assertions (both present in same test)
- Integration tests use real filesystem (`tmp_path`), not mocked I/O
- Threading guards verified by at least one real-thread test
- No OR-branch assertions in test bodies

---

### Step 5 — Output the report

Use this structure:

```
## Test Suite Assessment — <scope> — <date>

**<N> tests passing, <N> failing**  ← from pytest output

---

### Red Flags (fix immediately)

<finding: file path, which lesson, what was found, why it matters>
...

(none found — suite is clean on red-flag signals)

---

### Yellow Flags (address in next review)

<finding>
...

---

### Green Signals Confirmed

<pattern that is healthy and should be maintained>
...

---

### Summary

<2–3 sentences: overall health, most urgent item if any, one recommended next step>
```

---

## Notes

- Read files when needed — do not guess from filenames or test names
- Do not modify any source or test files during assessment
- Do not offer to fix findings unless the user explicitly asks
- Do not invent findings — if a signal is absent, say so
- If the user asks for a written report after reading the output, save it to
  `spec/TEST_SUITE_ASSESSMENT_<YYYYMMDD>.md`
