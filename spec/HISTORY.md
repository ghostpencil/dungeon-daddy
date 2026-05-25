# Dungeon Daddy — Session History Archive

---

## 2026-05-24 — Smoke test improvements (phase 7)

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
