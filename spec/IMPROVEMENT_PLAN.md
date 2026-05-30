# Dungeon Daddy — Improvement Plan

_Written: 2026-05-25. Based on a full assessment of the project at Post-18 Stabilisation._
_All items complete as of Stable Release milestone (2026-05-27)._

This document records actionable improvements across two dimensions: software
quality and AI SDLC practices. Items are ordered by impact, not difficulty.
Each item has a priority, a rough effort estimate, and concrete steps.

No item here changes the product's feature set. All are quality, tooling, or
process improvements suitable for a STABILIZATION phase or a dedicated
quality sprint.

---

## Quick Reference

| ID | Title | Priority | Effort | Status |
|---|---|---|---|---|
| IP-1 | CI: add lint, type-check, coverage | High | Small | **Done** |
| IP-2 | LLM observability | High | Medium | **Done** |
| IP-3 | Structured output for generator agent | High | Small | **Done** |
| IP-4 | Model configurable via environment | Medium | Small | **Done** |
| IP-5 | Formal skip markers for API-gated integration tests | Medium | Small | **Done** |
| IP-6 | Minimal AI output evals | Medium | Large | **Done** |
| IP-7 | Prompt versioning | Medium | Medium | **Done** |
| IP-8 | Consolidate requirements files into pyproject.toml | Low | Small | **Done** |
| IP-9 | Fix mypy None-guard issues in 6 deferred files | Medium | Small–Medium | **Done** |

---

## IP-1 — CI: Add Lint, Type-Check, and Coverage Gate

**Priority:** High  
**Effort:** Small (one CI file change, one pyproject.toml change)

### Problem

`mypy` strict mode and `ruff` are configured in `pyproject.toml` but neither
runs in CI. A green badge means tests pass — it does not mean the codebase is
type-correct or lint-clean. Coverage is never measured, so the 796-test count
has an unknown denominator.

### Steps

1. Add three steps to `.github/workflows/test.yml` after the existing
   `pytest` step:

   ```yaml
   - name: Lint
     run: ruff check .

   - name: Type-check
     run: mypy dungeon_daddy

   - name: Test with coverage
     run: pytest --ignore=tests/integration/test_ui_harness.py --cov=dungeon_daddy --cov-report=term-missing --cov-fail-under=70
   ```

2. Add `pytest-cov` to `requirements-dev.txt`.

3. Run `mypy dungeon_daddy` locally first and fix any existing errors before
   enabling in CI.

### Acceptance Criteria

- CI fails on any type error, lint violation, or coverage drop below threshold.
- Coverage report visible in CI logs.

---

## IP-2 — LLM Observability

**Priority:** High  
**Effort:** Medium

### Problem

There is no structured record of LLM calls: which agent made a call, what
prompt was sent, how many tokens were used, how long it took, or what it cost.
Without this, you cannot answer:

- Why did this session feel slow?
- How much does a typical play session cost?
- Did a prompt change degrade response quality?
- Which agent is responsible for most of the token spend?

The file logging is set up at app startup but logs are unstructured text.

### Steps

1. Add an `LLMCallRecord` dataclass to `dungeon_daddy/llm/provider.py` (or a
   new `dungeon_daddy/llm/telemetry.py`):

   ```python
   @dataclass
   class LLMCallRecord:
       agent: str           # "dm", "wizard", "generator", "design"
       model_id: str
       prompt_tokens: int
       completion_tokens: int
       duration_ms: float
       timestamp: str       # ISO-8601
   ```

2. Extend the `LLMProvider` protocol with an optional `last_usage` property
   that returns token counts (OpenAI SDK returns these on the response object).

3. Wrap each agent's `complete()` / `stream()` call with a timing block that
   writes a structured JSON line to a session log file in the user data
   directory (`AppConfig.user_data_dir / "llm_calls.jsonl"`).

4. Add a `tools/llm_cost_report.py` script that reads `llm_calls.jsonl` and
   prints a per-agent cost summary (using a configurable cost-per-1k-token
   table).

### Acceptance Criteria

- After a play session, `llm_calls.jsonl` contains one record per LLM call.
- The cost report script produces a per-agent token and cost breakdown.
- Unit tests for the record construction (no real LLM calls needed).

---

## IP-3 — Structured Output for Generator Agent

**Priority:** High  
**Effort:** Small

### Problem

`generator_agent.py` asks the model to return a JSON dungeon level. It then
parses the response as JSON. If the model returns malformed JSON or wraps the
JSON in a markdown code block, parsing fails. The `validate_dungeon` +
`auto_fix_dungeon` pipeline helps downstream, but the right fix is to enforce
the output shape at the API boundary.

OpenAI's `gpt-4o` supports `response_format={"type": "json_object"}` which
guarantees the response is valid JSON. It also supports full JSON Schema via
structured outputs.

### Steps

1. Update `OpenAIProvider` to accept an optional `response_format` parameter
   on `complete()`.

2. In `generator_agent.py`, pass `response_format={"type": "json_object"}` 
   when calling `complete()`.

3. Add a unit test asserting the provider is called with the correct format
   argument.

4. Optional (higher effort): define a full JSON Schema for the level structure
   and use OpenAI's `response_format={"type": "json_schema", "json_schema": ...}`
   to guarantee field names and types match the Pydantic model.

### Acceptance Criteria

- Generator agent calls fail loudly at the API boundary on malformed output,
  not silently downstream.
- `AnthropicProvider.complete()` ignores or logs-and-passes the
  `response_format` argument (Anthropic handles this differently).

---

## IP-4 — Model Configurable via Environment Variable

**Priority:** Medium  
**Effort:** Small

### Problem

The agent factory in `window.py` constructs `OpenAIProvider` with `"gpt-4o"`
hardcoded. Switching models or comparing quality across model versions requires
a code change and a redeployment.

### Steps

1. In `window.py` (or `config.py`), read the model ID from environment:

   ```python
   import os
   _DEFAULT_MODEL = "gpt-4o"
   model_id = os.getenv("DUNGEON_DADDY_MODEL", _DEFAULT_MODEL)
   ```

2. Pass `model_id` to `OpenAIProvider(model=model_id)`.

3. Update `.env.example` with `DUNGEON_DADDY_MODEL=gpt-4o`.

4. Add a unit test asserting that `AppConfig` (or the factory) reads the env
   var and passes it to the provider constructor.

### Acceptance Criteria

- Setting `DUNGEON_DADDY_MODEL=gpt-4o-mini` in `.env` switches the active
  model without code changes.

---

## IP-5 — Formal Skip Markers for API-Gated Integration Tests

**Priority:** Medium  
**Effort:** Small

### Problem

`tests/integration/test_llm_integration.py` requires `OPENAI_API_KEY`. In CI
this key is not set, so these tests silently pass or silently skip depending
on how the provider handles a missing key. This is invisible — the CI log
gives no indication that the LLM integration was not tested.

### Steps

1. Add a `pytest.ini` or `pyproject.toml` custom marker:

   ```toml
   [tool.pytest.ini_options]
   markers = [
       "live_api: requires a real API key; skipped in CI unless key is set",
   ]
   ```

2. Mark each test in `test_llm_integration.py`:

   ```python
   @pytest.mark.live_api
   @pytest.mark.skipif(
       not os.getenv("OPENAI_API_KEY"),
       reason="OPENAI_API_KEY not set"
   )
   def test_openai_complete_returns_string(): ...
   ```

3. CI command remains unchanged — the skip reason now appears in the test
   output, making the omission visible and intentional.

### Acceptance Criteria

- CI log shows `SKIPPED [N] tests/integration/test_llm_integration.py` with
  the `OPENAI_API_KEY not set` reason.
- Running locally with the key set executes the live tests.

---

## IP-6 — Minimal AI Output Evals

**Priority:** Medium  
**Effort:** Large

### Problem

The DM agent and wizard agent are the product's value proposition. The
integration tests verify the interface — they confirm agents call the provider
with a correctly constructed prompt. They do not verify that the wizard
produces coherent dungeon structures from user input, or that the DM maintains
narrative consistency across a session. Without evals, model upgrades or
prompt changes can silently degrade quality.

### Approach

A minimal eval framework does not need a dedicated library. It needs:

1. **Fixtures:** A small set of canonical inputs (dungeon concepts, room
   scenarios) stored in `tests/evals/fixtures/`.

2. **A scoring rubric per agent:**
   - _Generator agent:_ Does the output pass `validate_dungeon()` without
     auto-fix? Does it contain the requested number of rooms?
   - _Wizard agent:_ Does it ask at least one clarifying question? Does the
     generated dungeon name match the concept theme (keyword match)?
   - _DM agent:_ Does the response reference the current room's name? If room
     memory was injected, does the response use at least one detail from it?

3. **A baseline snapshot:** Run the evals once against `gpt-4o`, store the
   scores in `tests/evals/baseline_scores.json`. Future runs compare against
   this baseline.

### Steps

1. Create `tests/evals/` directory with `conftest.py` and a
   `pytest.mark.eval` marker.

2. Write `tests/evals/test_generator_evals.py` — 3–5 fixtures, real provider,
   assertions on structural validity.

3. Write `tests/evals/test_dm_evals.py` — 3–5 room scenarios, assertions on
   narrative coherence rules.

4. Add a `tools/run_evals.py` script that runs evals, prints pass/fail per
   fixture, and writes a JSON report.

5. Do not run evals in CI by default — mark them `@pytest.mark.eval` and
   exclude from the default `pytest` command. Run them manually before any
   model upgrade.

### Acceptance Criteria

- `pytest -m eval` runs evals against the live API and prints a score report.
- At least one eval would have caught the `save_name` persistence bug
  (memory saves silently skipped) if it had existed.

---

## IP-7 — Prompt Versioning

**Priority:** Medium  
**Effort:** Medium

### Problem

System prompts for the DM agent, wizard agent, generator agent, and design
agent are embedded in Python source files. There is no mechanism to:

- A/B test a new prompt variation against the baseline.
- Track which prompt version produced a given session's output.
- Roll back a prompt change that degraded quality.

### Steps

1. Create `dungeon_daddy/prompts/` directory.

2. Extract each agent's system prompt to a text file:
   - `dm_system.txt`
   - `wizard_system.txt`
   - `generator_system.txt`
   - `design_system.txt`

3. Add a `load_prompt(name: str) -> str` utility in
   `dungeon_daddy/llm/prompts.py` that reads from the `prompts/` directory
   (using `importlib.resources` for package-correct loading).

4. Update each agent to call `load_prompt("dm_system")` at init time and
   store the result as `self._system_prompt`.

5. Log the prompt filename (and a short hash) in the LLM call record from
   IP-2.

### Acceptance Criteria

- Changing a system prompt does not require touching agent code.
- The LLM call record includes which prompt file was used.
- Unit tests for `load_prompt()` verify file loading and missing-file error.

---

## IP-8 — Consolidate Requirements Files into pyproject.toml

**Priority:** Low  
**Effort:** Small

### Problem

The project defines dependencies in three places: `pyproject.toml`
(`[project.dependencies]`), `requirements.txt`, and `requirements-dev.txt`.
This creates a maintenance inconsistency — a new dependency could be added to
one file and forgotten in another.

### Steps

1. Move dev dependencies from `requirements-dev.txt` into `pyproject.toml`
   under `[project.optional-dependencies]`:

   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest>=8.3",
       "pytest-mock>=3.14",
       "pytest-cov>=5.0",
       "mss>=9.0",
   ]
   ```

2. Update CI install step from `pip install -r requirements-dev.txt` to
   `pip install -e ".[dev]"`.

3. Update the README install instructions.

4. Delete `requirements.txt` and `requirements-dev.txt`.

5. Keep `.env.example` — that is separate from package metadata.

### Acceptance Criteria

- `pip install -e ".[dev]"` installs everything needed to run tests.
- No `requirements.txt` or `requirements-dev.txt` files remain.
- CI passes after the change.

---

## IP-9 — Fix mypy None-guard and Structural Type Issues (6 Deferred Files)

**Priority:** Medium (quality debt)
**Effort:** Small–Medium (1–2 hours)
**Phase:** Post-18 Stabilisation — **DONE** (2026-05-27)
**Spec:** `spec/FEATURE_IP9_MYPY_NONE_GUARDS.md` (step-by-step tracking)

### Background

IP-1 left six files under `[[tool.mypy.overrides]] ignore_errors = true` in
`pyproject.toml`. These files have real type issues — not just annotation
style — that were too risky to fix during STABILIZATION.

Tracked in GitHub issue #2.

### Files and primary issues

| File | Errors | Root cause |
|---|---|---|
| `views/design_view.py` | 43 | None deref on `Dungeon \| None`, agent `\| None` attrs |
| `views/play_view.py` | 19 | None deref on `SessionState \| None`, bad assignments |
| `data/repository.py` | 15 | `Path \| None` used without guard throughout |
| `window.py` | 7 | Dict invariance, missing annotation |
| `llm/agents/dm_agent.py` | 22 | All params typed `object`; attribute access fails |
| `ui/panels/map_panel.py` | 7 | None deref on `Level \| None`, untyped callbacks |

### Steps

1. `repository.py` — add `assert self._dungeons_dir is not None` at the top
   of each method that accesses `self._dungeons_dir`. Lowest risk.

2. `dm_agent.py` — import `Room`, `Level`, `Dungeon`, `Loop` from
   `dungeon_daddy.data.models` and replace `object` parameter types.

3. `design_view.py` / `play_view.py` — add None guards before attribute
   access (`if self._dungeon is None: return`).

4. `window.py` — change `DungeonWizardAgent` param from `dict[str, object]`
   to `Mapping[str, LoopPattern]`; add missing annotation to one function.

5. `map_panel.py` — None guards + fix `on_click` redefinition pattern.

6. Remove all 6 entries from `[[tool.mypy.overrides]]` in `pyproject.toml`.

### Acceptance criteria

- `mypy dungeon_daddy` passes with zero per-file overrides for these 6 files.
- All tests still pass.

---

## Implementation Order Recommendation

For a STABILIZATION phase where only quality improvements are permitted, the
recommended order is:

1. **IP-5** (skip markers) — 30 minutes, zero risk, immediate CI clarity.
2. **IP-1** (CI lint/type/coverage) — 2–3 hours, fixes the measurement gap.
3. **IP-3** (structured output) — 2 hours, reduces a real failure mode.
4. **IP-4** (model env var) — 1 hour, unblocks model experimentation.
5. **IP-2** (observability) — 1 day, enables cost and quality tracking.
6. **IP-8** (requirements consolidation) — 1 hour, low risk.
7. **IP-7** (prompt versioning) — 1 day, prerequisite for repeatable evals.
8. **IP-6** (evals) — 2–3 days, the highest-value long-term investment.

Items IP-1 through IP-5 are suitable for STABILIZATION. Items IP-6 and IP-7
are best addressed in a dedicated quality sprint or at the start of the next
BUILD phase.

**IP-9** was discovered during IP-1 execution, tracked separately in GitHub issue #2,
and completed during the Post-18 Stabilisation phase.
