# Dungeon Daddy — Project Index

## Phase

Phase: Post-18 Stabilisation
Status: ONGOING — bug fixes and spec alignment only

754 unit tests + 42 integration tests = 796 passing (excl. UI harness).

---

## Current Work

Working through `spec/IMPROVEMENT_PLAN.md` in recommended order.
Tracked in GitHub: https://github.com/ghostpencil/dungeon-daddy/issues/1 — check off each item as it lands.

| ID | Title | Status |
|---|---|---|
| IP-5 | Formal skip markers for API-gated integration tests | TODO |
| IP-1 | CI: add lint, type-check, coverage | TODO |
| IP-3 | Structured output for generator agent | TODO |
| IP-4 | Model configurable via environment variable | TODO |
| IP-2 | LLM observability | TODO |
| IP-8 | Consolidate requirements files into pyproject.toml | TODO |
| IP-7 | Prompt versioning | TODO |
| IP-6 | Minimal AI output evals | TODO |

---

## Known Failures

_None._

---

## Recent Session

**2026-05-24 — Switch to Play menu fix + mock policy**

- Menu item now wired correctly; `set_switch_to_play_enabled` added to window.
- `spec/TESTING.md`: new Mock Policy section with mandatory-mock table, `__new__` recipe, right/wrong example.
- `tests/integration/test_play_menu.py` added (4 tests).
- 754 unit tests + 42 integration tests = 796 passing.

_Full history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- Improvement plan: `spec/IMPROVEMENT_PLAN.md`.
