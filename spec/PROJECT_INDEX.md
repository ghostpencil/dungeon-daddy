# Dungeon Daddy — Project Index

## Phase

Phase: Post-18 Stabilisation — Smoke Test Improvements
Status: COMPLETE

745 unit tests passing. SI-1 through SI-12 all done.
Smoke test (phase 7) upgraded to vision-guided Strategy B with chat logging.
Full plan in `spec/TEST_SUITE_IMPROVEMENT.md`. Audit findings in `spec/TEST_SUITE_ASSESSMENT_20260523.md`.

---

## Active Work — Test Suite Improvements

Full detail in `spec/TEST_SUITE_IMPROVEMENT.md`. Audit report in `spec/TEST_SUITE_ASSESSMENT_20260523.md`.

```
SI-1   LLM error paths                  DONE  769t
SI-2   Fix weak assertions              DONE
SI-3   View state mutations             DONE
SI-4   Memory file corruption recovery  DONE
SI-5   Generator output conflicts       DONE
SI-6   Routing edge cases               DONE
SI-7   Thread lifecycle (PlayView)      DONE  769 tests passing

SI-8   OR-branch assertions             DONE  test_generator_agent.py:431,439,463,464
SI-9   No-crash contract assertions     DONE  test_design_view.py:548, test_level_stepper.py:100,103, test_map_panel_zoom.py:169
SI-10  Unblock routing validation       DONE  tomb.json + crucible.json already in tests/fixtures/ — 102 tests run
SI-11  DesignView real-thread guard     DONE  new test_design_view_threading.py (3 tests: wizard x2, edit x1)  772t
SI-12  Tighten integration assertions   DONE  test_llm_integration.py:61,71,91
```

---

## Completed Work

**F-31 — Test Drive vs. Start Play** — DONE

```
Step 1a  tests/unit/views/test_play_view.py            DONE
Step 1b  dungeon_daddy/views/play_view.py               DONE
Step 2a  tests/unit/views/test_window.py                DONE
Step 2b  dungeon_daddy/window.py                        DONE
Step 3a  tests/unit/ui/panels/test_inspector_panel.py   DONE
Step 3b  dungeon_daddy/ui/panels/inspector_panel.py     DONE
Step 4a  tests/unit/views/test_design_view.py           DONE
Step 4b  dungeon_daddy/views/design_view.py             DONE
```

---

## Known Failures

_None._

---

## Session History

**2026-05-24 — Smoke test improvements (phase 7)**

- `tools/smoke_test_phase7.py` rewritten from hardcoded pixel script to vision-guided Strategy B
- `_wizard_next_step` now returns step name + DM response text in a single classifier call (JSON response format with regex fallback for malformed responses)
- `error_detected` terminal step added — wizard stops immediately on ⚠ error in chat
- `_vision_assert` replaces pixel color checks for DungeonTree level assertion
- Structured chat log (`_ChatEntry`) written to `tools/screenshots/` after each run — turn-by-turn record of action, GM message sent, DM response, and screenshot filename
- `design_view._handle_level_result` fixed to retry on parse errors (not just validation errors) up to 3 times — passes parse error message back to generator as a validation hint
- Generator prompt updated: explicit uniqueness constraint on `main_loop_role` within a loop
- 2 new unit tests added: `test_on_update_level_result_parse_error_retries_with_error`, `test_on_update_level_result_parse_error_exhausted_shows_error`
- Chat log analysis revealed wizard asks room clarification questions — `send_clarification` step added, `send_nudge` message updated to preemptively answer common clarifications
- 745 unit tests passing. Smoke test phase 7 passing end-to-end.

---

## Completed Work — Smoke Test Phase 13 Strategy B Upgrade

`tools/smoke_test_phase13.py` upgraded to match phase 7 Strategy B improvements.

```
ST13-1  JSON classifier + regex fallback    DONE
ST13-2  error_detected terminal step        DONE
ST13-3  Chat log (_ChatEntry + writer)      DONE
ST13-4  _vision_assert post-wizard check    DONE
ST13-5  Run and verify end-to-end           DONE  ALL BEHAVIORS PASSED
```

---

## Next Session

**Goal: Publish to GitHub as ghostpencil/dungeon-daddy**

Pre-publish fixes already done (2026-05-24):
- README rewritten to explain dual purpose (GM assistant + teaching experiment)
- `.claude/settings.local.json` added to `.gitignore`
- README screenshots un-ignored in `tools/.gitignore`
- All URLs updated to `ghostpencil` account
- Contributing section added (not accepting external PRs yet)

Remaining steps:
1. `git init` and make initial commit
2. Create repo via `gh repo create ghostpencil/dungeon-daddy --public`
3. Push to GitHub
4. Verify CI badge is live and README renders correctly
5. Share link with team

---

## Spec Loading Guide

Default: do not open specs.

Open only if needed:

- UI behavior or layout → `UI_SPEC.md`
- Colors, fonts, drawing → `VISUAL_DESIGN.md`
- State / threading / view ownership → `ARCHITECTURE.md`
- Writing or modifying tests → `TESTING.md`
- Expected feature behavior → `FEATURES.md`
- Phase history / exit criteria → `IMPLEMENTATION_PHASES.md`

Do not open:
- `TECH_STACK.md` (only if adding/changing a library)

---

## Skills

- Use TDD skill before writing new test files or defining test strategy
- Do not use for simple bug fixes without test changes
- Use `/ui-test` skill to verify UI behavior against a live window after each step with visible output

---

## Notes

- TDD required — write tests first
- All LLM calls use dependency-injected providers (mockable)
- No real API calls in unit tests — mock the provider
- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider
