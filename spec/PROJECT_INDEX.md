# Dungeon Daddy — Project Index

## Phase

Phase: Post-18 Stabilisation
Status: ONGOING — bug fixes and spec alignment only

754 unit tests + 42 integration tests = 796 passing (excl. UI harness).
Full plan in `spec/TEST_SUITE_IMPROVEMENT.md`. Audit findings in `spec/TEST_SUITE_ASSESSMENT_20260523.md`.

---

## Completed — Test Suite Improvements (SI-1 through SI-12)

All 12 items done. Full history in `spec/TEST_SUITE_IMPROVEMENT.md` and `spec/TEST_SUITE_ASSESSMENT_20260523.md`.

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

**2026-05-24 — Switch to Play menu fix + mock policy**

- `window._build_menu`: stores `_switch_to_play_action` reference; handler changed from `switch_mode("play")` to `_menu_launch_play` which mirrors the Start Play button (calls `launch_play_session` for saved dungeons with levels, silent no-op otherwise).
- `window.set_switch_to_play_enabled(enabled)`: new method mutates `_switch_to_play_action.enabled`.
- `design_view._refresh_play_button_state`: now calls `self.window.set_switch_to_play_enabled(is_saved)` so the menu item tracks the same save-state rule as the inspector button.
- `_make_overlay_view()` in `test_design_view.py`: added `view.window = MagicMock()` so existing overlay tests survive the new `window` call.
- `tests/integration/test_play_menu.py` added — 4 integration tests using real `DungeonDaddyWindow._build_menu()` + real `DesignView._refresh_play_button_state()` + real `DungeonRepository(tmp_path)`: save-state enables action, unsaved disables, menu handler routes to `launch_play_session`, save-then-refresh cycle flips flag end-to-end.
- `spec/TESTING.md`: new **Mock Policy** section — mandatory-mock table, wrong/right example, `__new__` recipe, rule of thumb. `test_play_menu.py` added to integration test index.
- `CLAUDE.md`: TDD skill section now requires reading `spec/TESTING.md` before invoking; spec loading rules list TDD skill invocation as first trigger for `TESTING.md`.
- 754 unit tests + 42 integration tests = 796 passing.

---

**2026-05-24 — Play-mode bug fixes + memory integration tests**

- `play_view.save_memory_overlay`: removed `_is_test_drive` guard — saves were silently skipped in test-drive even though `_auto_remember` already writes to `__test_drive__/memory/` unconditionally; inconsistency caused edits to disappear after clicking Save. Test renamed and updated.
- `window.save_dungeon`: stamp `dungeon.meta.save_name = name` before writing to disk so `save_name` persists in JSON. `window.open_dungeon`: back-fill `save_name` from folder name when loading older files. Without this, `_is_saved` was always False and "Start Play →" was permanently greyed out. Two new regression tests added.
- `tests/integration/test_memory_integration.py` added — 9 integration tests using real `DungeonRepository(tmp_path)`: play-mode and test-drive save/reload cycles, namespace isolation, `append_room_event` vs `save_memory_overlay` consistency contract, `save_name` round-trip. These would have caught both bugs before they shipped.
- 747 unit tests + 9 new integration tests = 780 passing (excl. UI harness).

---

## Published

**https://github.com/ghostpencil/dungeon-daddy** — published 2026-05-24

- Initial commit: 198 files, 745 unit tests passing
- CI badge live and green (771 passing in CI, 3 UI harness tests excluded — require OpenGL)
- 14 GitHub topics set for discoverability
- Presentation PDF included; PPTX excluded from repo

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider
- Spec loading rules and skills are in `CLAUDE.md` (canonical source)
