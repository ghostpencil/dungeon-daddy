# Next Slice

Bootstrap a fresh session onto the next slice of the current phase: orient → confirm scope
(one question) → branch → TDD. Process reference: `spec/SDLC.md`.

## How to use

`/next-slice` — first command in a fresh session. Optional argument to name a specific
slice: `/next-slice B3` or `/next-slice the telemetry try/finally item`.

## Workflow

### 1. Orient

Read `spec/PROJECT_INDEX.md` (CLAUDE.md is already loaded). From its Phase section and
START HERE, determine:
- Phase mode (BUILD vs STABILIZATION) — phase discipline in CLAUDE.md applies.
- The current phase spec (`spec/PHASE_NN_*.md`); read it if one exists for this phase.
- The next unstarted slice and its exit criteria. If an argument named a slice, use that
  instead — but flag it if PROJECT_INDEX suggests a different order.

Load no other spec files yet (context-minimization rule); pull them in later only when the
slice touches their area.

### 2. Confirm scope — the ONE owner halt

Ask one question (AskUserQuestion): the slice you propose to do, its exit criteria in a
sentence or two, and what it deliberately does NOT include. Offer the next-best alternative
slice as a second option. Do not proceed until answered; do not ask anything else unless a
genuine design question surfaces later.

### 3. Ensure the branch

- If a phase/cleanup branch already exists for this work, check it out and `git pull`.
- If on `main` with no branch yet, create one: `feat/phase-NN-<slug>` (BUILD) or
  `chore/cleanup-<slug>` (STABILIZATION), branched off up-to-date `main`.
- Never implement a slice directly on `main`.

### 4. Enter the TDD loop

1. Read `spec/TESTING.md` — fresh, every time; do not rely on memory.
2. Invoke the TDD skill.
3. Implement the slice in small red–green–refactor cycles, one behavior at a time.
4. A spec conflict or owner-facing design decision HALTS with a question — never resolve
   one silently.

### 5. Finish

When the slice's exit criteria are met, tell the owner the slice is ready for close-out
and run `/end-slice` (gate, review, commit, PROJECT_INDEX, then `/clear`).

## Notes

- One slice per session. If the confirmed slice turns out to hide two behaviors, finish
  the first, note the second in PROJECT_INDEX via `/end-slice`, and take it next session.
- If PROJECT_INDEX and the phase spec disagree about what is next, PROJECT_INDEX is newer
  — trust it, and fix the spec as part of the slice's docs commit.
