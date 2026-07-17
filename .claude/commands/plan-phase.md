# Plan Phase

Turn a phase idea into a build-ready `spec/PHASE_NN_*.md` by **interrogating the owner**
and **adversarially attacking the requirements** until no material gaps remain. The spec
is written last, not first. Process reference: `spec/SDLC.md`.

Prime directive: **never fill a gap with an assumption.** Every gap, ambiguity, or
contradiction becomes a question to the owner. If the owner answers "you decide," record
your choice as a numbered decision marked *(proposed)* and get it approved with the final
spec — silence is never approval.

## How to use

`/plan-phase` — at a phase boundary, or when `/next-slice` finds nothing to slice.
Optional argument to skip candidate selection: `/plan-phase 52` or
`/plan-phase monster reactions`.

## Workflow

### 1. Orient

Read `spec/PROJECT_INDEX.md` (Notes + deferred backlog + Product Direction). Then, only
as needed: `spec/RPG_MEMORY_ROADMAP.md` (sequence, thesis, non-goals),
`spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (planned next phases), any design doc named
for the candidate (e.g. `spec/MONSTER_REACTION_DESIGN.md`), `spec/FEATURES.md` (scope).

### 2. Candidate selection — owner halt 1

Present the candidate phases (roadmap order, deferred backlog pressure, anything the
owner raised) with a recommendation and a one-line value statement each. AskUserQuestion.
Record the choice as OWNER-DECIDED with the date.

### 3. Requirements interview — grill in rounds

Interview the owner with AskUserQuestion in batches (≤4 questions per round). Prefer
concrete options with trade-offs over open-ended questions; use previews (mock
transcripts, ASCII UI sketches) when the difference is visual. Keep going until a full
round surfaces nothing new. Cover, minimum:

- **Player-visible value** — what does the GM/player actually see or do differently?
  Ask for a worked example: "walk me through one round of play using this."
- **Scope edges** — for each borderline capability: in or out? Everything cut goes to
  Non-Goals by name, so it can't creep back silently.
- **Behavior specifics** — for each behavior: trigger, inputs, engine rule, output,
  and what the player sees. Vague verbs ("handles", "reacts", "manages") are not
  answers — push for the rule.
- **Authority split** — for anything the LLM touches: propose-and-validate, read-only,
  or pure narration? "The LLM decides X" is a red flag to resolve, not record.
- **Failure & emptiness** — what happens when the LLM call fails, the table is empty,
  the target is dead/absent, the action repeats, the save predates the feature?
- **Tuning** — which numbers are balance constants (→ `spec/BALANCE_NOTES.md`) vs
  structural rules?

### 4. Adversarial gap analysis — attack the requirements

After the interview, actively try to break the requirements. Run every sweep; each
finding becomes either a new interview question (back to step 3) or a recorded decision:

- **Transcript walk** — write a short play transcript exercising the feature end to end.
  Every moment the transcript forces you to invent something unspecified is a gap.
- **Authority sweep** — scan for any behavior where the LLM mutates authoritative state.
  The engine disposes; violations get redesigned as proposal + validator or engine rule
  (`docs/LLM_AUTHORITY_BOUNDARY.md`).
- **Cross-system sweep** — does the feature read or write clocks, memories/tags,
  objectives, inventory, room objects, navigation, dungeon voice, playbooks, stress?
  Each touched system needs a stated interaction rule (or an explicit "unaffected").
- **Persistence sweep** — new/changed models → migration number, seed data, and the
  live-save question: what happens on The Crucible with existing data? (Existing saves
  skip backfills — see PROJECT_INDEX gotchas.) Preserve-and-extend; never break saves.
- **Testability sweep** — every behavior must be pinnable by a deterministic test, or
  explicitly assigned to the eval suite or the owner UI checklist. "Feels right" is not
  an exit criterion.
- **Contradiction sweep** — check the answers against each other, against Product
  Direction, and against locked decisions in prior specs (e.g. 51.5 D1–D8). Surface
  conflicts; never quietly pick a side.
- **Minimal-version attack** — what is the smallest version that still delivers the
  value? Anything above that line must be justified or moved to a later phase.

Optionally spawn an Explore agent to verify feasibility claims against the codebase
(does the seam we're assuming exist?) before locking decisions that depend on them.

### 5. Draft the spec

Only when Open Questions is empty (or contains only *(proposed)* decisions awaiting the
step-6 approval), write `spec/PHASE_NN_<SLUG>.md`:

```
# Phase NN — Title
## Goal                (player-visible value, 2–3 sentences)
## Owner Decisions     (D1… numbered, dated; (proposed) items flagged)
## Behaviors           (B1… — trigger, rule, output, what the player sees)
## Non-Goals           (everything cut, by name)
## Authority Boundary  (what the LLM may propose/read; what only the engine does)
## Data & Migration    (models, migration NNN, seed, live-save/Crucible impact)
## UI Surface          (views/panels touched + owner UI review checklist for /end-phase)
## Slices              (S1… in dependency order — scope, exit criteria, test approach each)
## Risks & Deferred    (known risks, explicitly deferred items)
```

Slices must each be one-session-sized with exit criteria a test (or the UI checklist)
can verify. Behaviors map onto slices — no behavior left unassigned.

### 6. Approval — owner halt

Present the spec: decision list (flagging *(proposed)* ones), slice breakdown, and the
top 3 risks. On approval: create `feat/phase-NN-<slug>` off up-to-date `main`, flip
`spec/PROJECT_INDEX.md` to BUILD with the spec pointer and OWNER-DECIDED note, commit
the spec + index (docs commit), and hand off: **`/clear`, then `/next-slice`.**

## Notes

- Rounds of ≤4 questions beat one giant questionnaire — later questions should depend
  on earlier answers.
- If interrogation stalls ("I don't know yet"), park the behavior in Risks & Deferred
  and shrink the phase rather than spec on guesses.
- A phase plan that survives step 4 unchanged is a smell — attack harder.
