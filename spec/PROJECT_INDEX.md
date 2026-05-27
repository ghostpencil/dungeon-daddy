# Dungeon Daddy — Project Index

## Phase

Phase: Post-18 Stabilisation
Status: ONGOING — bug fixes and spec alignment only

799 unit/integration tests passing (excl. UI harness and 3 live-API tests).

---

## Current Work

Working through `spec/IMPROVEMENT_PLAN.md` in recommended order.
Tracked in GitHub: https://github.com/ghostpencil/dungeon-daddy/issues/1 — check off each item as it lands.

| ID | Title | Status |
|---|---|---|
| IP-5 | Formal skip markers for API-gated integration tests | DONE |
| IP-1 | CI: add lint, type-check, coverage | DONE |
| IP-3 | Structured output for generator agent | DONE |
| IP-4 | Model configurable via environment variable | DONE |
| IP-2 | LLM observability | DONE |
| IP-8 | Consolidate requirements files into pyproject.toml | TODO |
| IP-7 | Prompt versioning | TODO |
| IP-6 | Minimal AI output evals | TODO |
| IP-9 | Fix mypy None-guard issues in 6 deferred files | TODO (next BUILD phase) |

---

## Known Failures

_None._

---

## Recent Session

**2026-05-27 — IP-1: CI lint, type-check, and coverage gate**

- Added `ruff check .`, `mypy dungeon_daddy`, and `pytest --cov` steps to `.github/workflows/test.yml`.
- Added `pytest-cov>=5.0` to `requirements-dev.txt` and `pyproject.toml [project.optional-dependencies]`.
- Fixed all ruff violations across source and tests (227 auto-fixed, 51 manual).
- Fixed all mypy errors: mechanical type-arg fixes, targeted `# type: ignore` for SDK/duck-typing,
  and per-file `ignore_errors` overrides for 6 complex files needing architectural None-guard work.
- Coverage gate at 70%: currently at 74%.
- 791 non-live tests passing.

**2026-05-27 — IP-3: Structured output for generator agent**

- Added `response_format: dict[str, str] | None = None` to `LLMProvider` Protocol, `OpenAIProvider.complete()`, and `AnthropicProvider.complete()`.
- `OpenAIProvider` forwards the param to the SDK when set (conditional branch to preserve existing `arg-type` ignore).
- `AnthropicProvider` accepts but ignores it (Anthropic doesn't support this param).
- `DungeonGeneratorAgent.generate_level()` passes `response_format={"type": "json_object"}`.
- Updated system prompt: removed markdown fence instruction; now says "Output only valid JSON. No prose, no markdown."
- `parse_level()` now accepts raw JSON (no ``` fence) as well as the old fenced form.
- 796 non-live tests passing.

**2026-05-27 — IP-4: Model configurable via environment variable**

- Added `_get_model_id()` to `window.py`: reads `DUNGEON_DADDY_MODEL` env var, falls back to `"gpt-4o"`.
- Both `_build_dm_agent()` and `_build_agents()` now pass `model=_get_model_id()` to `OpenAIProvider`.
- Added `DUNGEON_DADDY_MODEL=gpt-4o` to `.env.example`.
- 3 new unit tests: default fallback, env override, factory passes model to provider.
- 799 non-live tests passing.

**2026-05-27 — IP-5: Formal skip markers for API-gated integration tests**

- Registered `live_api` marker in `pyproject.toml` `[tool.pytest.ini_options]`.
- Added `@pytest.mark.live_api` to all 3 tests in `tests/integration/test_llm_integration.py`.
- CI log now shows skip reason explicitly when `OPENAI_API_KEY` is not set.
- 788 non-live tests passing.

**2026-05-27 — IP-2: LLM observability**

- Added `LLMCallRecord` dataclass and `TelemetryWriter` to `dungeon_daddy/llm/telemetry.py`.
- Added `ObservingProvider` wrapper: times each `complete()`/`stream()` call, reads `last_usage` from the inner provider, appends one JSON line to `llm_calls.jsonl` in `AppConfig.user_data_dir`.
- Added `last_usage: tuple[int, int] | None` property to `OpenAIProvider` (and `LLMProvider` Protocol): populated from response token counts after each `complete()` call.
- Wired `ObservingProvider` in `window.py`: `_build_dm_agent()` and `_build_agents()` now wrap their providers with agent names "dm", "wizard", "generator", "design".
- Added `tools/llm_cost_report.py`: reads `llm_calls.jsonl`, prints per-agent token and cost breakdown. Cost table configurable via `LLM_COST_INPUT`/`LLM_COST_OUTPUT` env vars.
- 813 non-live tests passing (14 new in `tests/unit/llm/test_telemetry.py`).

_Full history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- Improvement plan: `spec/IMPROVEMENT_PLAN.md`.
