# Dungeon Daddy — SDLC

Canonical description of the development process. The commands `/next-slice`, `/end-slice`,
and `/end-phase` (in `.claude/commands/`) automate it; if this file and a command disagree,
this file wins — fix the command.

---

## Shape

Work is organized as **phases → slices → TDD cycles**.

- A **phase** delivers one feature or a set of related features. It lives on one branch
  (`feat/phase-NN-<slug>`), has a spec (`spec/PHASE_NN_*.md`) that breaks it into slices,
  and ends in a single PR to `main`.
- A **slice** is one coherent behavior within a phase — small enough for a single session.
  Each slice is built test-first, reviewed, committed, and recorded before context is cleared.
- A **TDD cycle** is one red–green–refactor step inside a slice.

During **STABILIZATION** there are no feature phases; the same slice loop applies to
bug-fix/cleanup slices on a cleanup branch.

## Owner halt points

The process runs autonomously except at these five points. Everything else (gates, reviews,
fix application, bookkeeping, commits) proceeds without asking.

1. **Phase scope** — the owner decides what the next phase (or cleanup slice) covers.
   Recorded as OWNER-DECIDED in `spec/PROJECT_INDEX.md` START HERE.
2. **Slice scope confirmation** — one question at the start of `/next-slice`.
3. **Design questions** — any spec conflict or owner-facing design decision surfaced
   mid-slice halts with a question; it is never resolved silently.
4. **UI review** — the owner verifies the GUI personally at phase end (never driven by
   computer-use on the owner's behalf).
5. **Merge approval** — the owner approves the PR merge.

## The Gate

"The gate" means all three, in order, all green:

```
python -m ruff check .
python -m mypy dungeon_daddy        # strict; green baseline — any new error is a regression
python -m pytest -q                 # full suite; evals auto-excluded via addopts
```

The same checks run in CI (workflow `Tests`, job `test`, which additionally enforces
coverage ≥ 70%). Branch protection on `main` requires the `test` check on PRs; direct
pushes by the owner (docs/spec commits) are exempt.

A PostToolUse hook additionally runs `ruff` + `mypy` on every edited `.py` file, so most
gate failures surface at edit time rather than at slice end.

## Phase start

1. Owner states phase scope *(halt 1)*.
2. Phase plan written to `spec/PHASE_NN_*.md`: goal, slices in dependency order, exit
   criteria per slice, non-goals. Owner approves the slice breakdown.
3. Branch `feat/phase-NN-<slug>` created off `main`.
4. `spec/PROJECT_INDEX.md` updated: phase status BUILD, pointer to the spec.

## Slice loop (repeat per slice)

Run `/next-slice` in a **fresh session**:

1. Read `CLAUDE.md` + `spec/PROJECT_INDEX.md`, then the phase spec. Load no other specs
   until needed (context-minimization rule).
2. Identify the next unstarted slice and its exit criteria; confirm scope with the owner
   in one question *(halt 2)*.
3. Ensure the phase branch is checked out (create it if phase start was skipped).
4. Read `spec/TESTING.md`, invoke the TDD skill, implement the slice in small
   red–green–refactor steps. Design questions halt *(halt 3)*.

Run `/end-slice` when the slice's exit criteria are met:

5. Run the gate.
6. Slice code review (code-review on the diff). Apply CRITICAL/HIGH fixes now; defer the
   rest to the PROJECT_INDEX backlog with a one-line rationale each. Re-run the gate if
   anything changed.
7. Commit (heredoc for multi-line messages, via the Bash tool).
8. Update `spec/PROJECT_INDEX.md` — slice marked done, deferred items appended — and
   commit the docs change.
9. Owner clears context (`/clear`). Every slice starts from a fresh window.

## Phase end

Run `/end-phase` when the last slice is done:

1. Run the gate; run the phase smoke test / UI-harness coverage where the spec calls for it.
2. **Owner UI review** *(halt 4)* — owner runs `python -m dungeon_daddy` and verifies the
   phase's visible behavior. Findings become fix commits (back to the slice loop if large).
3. Push and open the PR (`gh`), body summarizing the phase against its exit criteria.
4. Whole-arc review: `pr-review-toolkit:review-pr` on the PR. Apply fix batches, re-run
   the gate, push. Deeper option when warranted: `/code-review ultra <PR#>`.
5. **Merge approval** *(halt 5)*, then merge.
6. Post-merge bookkeeping on `main`: PROJECT_INDEX Phase History row + status flip,
   deferred-pile consolidation, spec cleanup, memory updates worth keeping.

## Bookkeeping rules

- `spec/PROJECT_INDEX.md` is the single source of truth for phase/slice status, the
  deferred backlog, and START HERE. It is updated at every slice end and phase end —
  never left for "later".
- Owner decisions are recorded where they were made (PROJECT_INDEX or the phase spec)
  with the date.
- Deferred review findings go to the backlog, not into scope creep; a big enough pile
  becomes a cleanup slice by owner decision.
