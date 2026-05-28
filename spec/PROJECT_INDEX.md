# Dungeon Daddy — Project Index

## Phase

Phase: Post-18 Stabilisation
Status: ONGOING — bug fixes and spec alignment only

849 unit/integration tests passing (excl. UI harness and 3 live-API tests).
6 eval tests passing (run with `pytest -m eval` or `python tools/run_evals.py`).

---

## Current Work

| ID | Title | Status |
|---|---|---|
| IP-5 | Formal skip markers for API-gated integration tests | DONE |
| IP-1 | CI: add lint, type-check, coverage | DONE |
| IP-3 | Structured output for generator agent | DONE |
| IP-4 | Model configurable via environment variable | DONE |
| IP-2 | LLM observability | DONE |
| IP-8 | Consolidate requirements files into pyproject.toml | DONE |
| IP-7 | Prompt versioning | DONE |
| IP-6 | Minimal AI output evals | DONE |
| IP-9 | Fix mypy None-guard issues in 6 deferred files | DONE |
| MC-1 | Markdown rendering in chat panels (Design + Play) | DONE |

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

**2026-05-27 — IP-8: Consolidate requirements files into pyproject.toml**

- Deleted `requirements.txt` and `requirements-dev.txt` — all deps were already in `pyproject.toml`.
- Updated CI install step: `pip install -r requirements-dev.txt` → `pip install -e ".[dev]"`.
- Updated `cache-dependency-path` in CI from `requirements-dev.txt` to `pyproject.toml`.
- Updated README: installation uses `pip install -e .`; dev setup uses `pip install -e ".[dev]"`.
- 813 non-live tests still passing.

**2026-05-27 — IP-2: LLM observability**

- Added `LLMCallRecord` dataclass and `TelemetryWriter` to `dungeon_daddy/llm/telemetry.py`.
- Added `ObservingProvider` wrapper: times each `complete()`/`stream()` call, reads `last_usage` from the inner provider, appends one JSON line to `llm_calls.jsonl` in `AppConfig.user_data_dir`.
- Added `last_usage: tuple[int, int] | None` property to `OpenAIProvider` (and `LLMProvider` Protocol): populated from response token counts after each `complete()` call.
- Wired `ObservingProvider` in `window.py`: `_build_dm_agent()` and `_build_agents()` now wrap their providers with agent names "dm", "wizard", "generator", "design".
- Added `tools/llm_cost_report.py`: reads `llm_calls.jsonl`, prints per-agent token and cost breakdown. Cost table configurable via `LLM_COST_INPUT`/`LLM_COST_OUTPUT` env vars.
- 813 non-live tests passing (14 new in `tests/unit/llm/test_telemetry.py`).

**2026-05-27 — IP-7: Prompt versioning**

- Created `dungeon_daddy/prompts/` package with 5 `.txt` files: `dm_system`, `wizard_phase1_system`, `wizard_phase2_system`, `generator_system`, `design_system`.
- Added `dungeon_daddy/llm/prompts.py`: `load_prompt(name)` (uses `importlib.resources`) and `prompt_hash(text)` (SHA-256 first 8 hex chars).
- Updated all four agents to call `load_prompt()` at `__init__` and use `self._system_prompt` / `self._phase1_prompt` / `self._phase2_prompt` in their methods.
- Added `prompt_name: str = ""` and `prompt_hash: str = ""` fields to `LLMCallRecord`.
- Extended `ObservingProvider.__init__` to accept `prompt_name`/`prompt_hash`; includes them in every written record.
- Updated `window.py` `_build_dm_agent()` and `_build_agents()` to load the primary prompt, hash it, and pass both to `ObservingProvider`.
- Added `[tool.setuptools.package-data]` in `pyproject.toml` so `.txt` files are included in distributions.
- 6 new tests in `tests/unit/llm/test_prompts.py` and `test_telemetry.py`.
- 819 non-live tests passing.

**2026-05-27 — MC-1: Markdown rendering — Steps 5–6 + wizard parse_brief bug fix**

- Step 5 — `_bubble_height(index, msg, bubble_w)`: replaced character-count heuristic with `label.content_height + PAD_SM*2 + _LABEL_H`; bubbles now resize to fit formatted content exactly.
- `_compute_heights` updated to pass the message index to `_bubble_height`.
- Step 6 — `_draw_messages_inner`: removed `text_w` parameter; replaced `arcade.draw_text(msg.content, …)` with `label.update_position(…); label.draw()` — bold, italic, code, headings, and bullets all render via pyglet HTMLLabel.
- Removed dead constants `_CHARS_PER_PX` and `_LINE_H`; removed unused `text_color` local.
- Bug fix — `wizard_agent.parse_brief`: `int(data["num_levels"])` crashed when LLM returned `"3 levels of moderate complexity"`; added `_int()` helper that extracts the first digit from any value.
- 5 new tests (Steps 5–6) + 1 new regression test for the parse_brief bug.
- smoke_test_phase7.py: all 5 behaviors PASS — full wizard → generation → play flow confirmed.
- 849 unit/integration tests passing.

**2026-05-27 — MC-1: Markdown rendering — Steps 1–4 (md_to_html + MarkdownLabel + label cache)**

- Created `dungeon_daddy/ui/widgets/markdown_label.py` with `_rgb_to_hex()`, `md_to_html()`, and `MarkdownLabel`.
- `md_to_html()` applies 6 rules in order: headings (h1/h2/h3 with teal color + size), bold, italic, inline code (JetBrains Mono), bullets (`-`/`*` → `•`), `\n` → `<br>`.
- `MarkdownLabel` wraps `pyglet.text.HTMLLabel` with `content_height`, `draw()`, and `update_position()`.
- Added `_label_cache: dict[int, MarkdownLabel]` to `ChatPanel.__init__`.
- Added `_get_or_build_label(index, msg, bubble_w)` — lazy cache; builds `MarkdownLabel` on first access per index.
- `resize()` and `teardown()` both call `_label_cache.clear()`.
- 5 new tests in `tests/unit/ui/test_chat_panel.py` — all passing.
- 844 unit/integration tests passing.

**2026-05-27 — IP-9: Fix mypy None-guard issues (all 7 steps)**

- Steps 1–4 (prior session): `repository.py`, `dm_agent.py`, `design_view.py`, `play_view.py`.
- Step 5 — `window.py`: added `DungeonMasterAgent | None` return type to `_build_dm_agent`; proper typed tuple return for `_build_agents`; added TYPE_CHECKING imports for agent/model types; typed `open_dungeon` params as `Callable`; typed `launch_test_drive`/`launch_play_session` params as `Dungeon`.
- Step 6 — `ui/panels/map_panel.py`: added type args to `_tab_style` return; added `assert lvl is not None` in `_draw_level_overlay`; added `# type: ignore[no-untyped-call]` for arcade `trigger_render()`; moved `# type: ignore[no-redef]` to decorator line for second `on_click`.
- Step 6 (also) — `llm/telemetry.py`: added `last_usage` property to `ObservingProvider` to satisfy `LLMProvider` protocol.
- Step 6 (also) — `llm/agents/wizard_agent.py`: changed `loop_patterns` param from `dict[str, object]` to `Mapping[str, LoopPattern]`; removed stale `# type: ignore[attr-defined]`.
- Step 7 — Removed final 2 entries from `[[tool.mypy.overrides]]`; `mypy dungeon_daddy` clean across all 47 files with zero overrides.
- 824 unit/integration tests still passing.

**2026-05-27 — IP-6: Minimal AI output evals**

- Created `tests/evals/` with `conftest.py` (module-scoped `provider` fixture, skips without key).
- Created `tests/evals/fixtures/dungeon_fixtures.py`: canonical briefs and room/level/dungeon objects.
- Added `tests/evals/test_generator_evals.py`: 3 evals sharing one API call — level parseable, passes `validate_dungeon()`, has ≥2 rooms.
- Added `tests/evals/test_dm_evals.py`: 3 evals — response references room name, uses injected memory, produces `[REMEMBER:` tag on action.
- Added `tools/run_evals.py`: runs `pytest -m eval`, writes/compares `tests/evals/baseline_scores.json`.
- Registered `eval` marker in `pyproject.toml`; added `--ignore=tests/evals` to CI pytest command.
- 6/6 evals passing; baseline scores saved.
- 819 non-live/non-eval tests still passing.

_Full history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- Improvement plan: `spec/IMPROVEMENT_PLAN.md`.
