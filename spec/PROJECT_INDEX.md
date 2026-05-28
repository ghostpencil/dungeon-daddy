# Dungeon Daddy — Project Index

## Phase

Phase: Post-18 Stabilisation
Status: COMPLETE — stable release (2026-05-27)

849 unit/integration tests passing (excl. UI harness and 3 live-API tests).
6 eval tests passing (run with `pytest -m eval` or `python tools/run_evals.py`).

---

## Known Failures

_None._

---

## Stable Release — 2026-05-27

All 10 improvement plan items (IP-1 through IP-9, MC-1) complete. Codebase is
lint-clean (`ruff`), fully type-checked (`mypy` zero errors, zero overrides),
and at 74% test coverage with a 70% CI gate. Prompt versioning, LLM
observability, structured output, model env-var switching, and minimal AI evals
are all in place.

Next step: define new feature goals or start a new BUILD phase.

_Full session history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
- Improvement plan: `spec/IMPROVEMENT_PLAN.md`.
