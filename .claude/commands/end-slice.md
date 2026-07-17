# End Slice

Close out the current slice: gate → review → fix → commit → record. Runs without asking
except for owner-facing design questions. Process reference: `spec/SDLC.md`.

## How to use

`/end-slice` — after the slice's exit criteria are met, before `/clear`.

## Workflow

### 1. Sanity check

- `git status` + `git diff --stat`. If the working tree is clean and nothing is
  uncommitted, report that there is no slice to close and stop.
- Confirm you are NOT on `main`. If you are, stop and say so — slices live on a phase or
  cleanup branch.

### 2. Run the gate

```
python -m ruff check .
python -m mypy dungeon_daddy
python -m pytest -q
```

All three must be green. If not, fix the failures first (TDD skill rules apply if tests
change), then re-run. Do not proceed on red. mypy is a green strict baseline — any new
error is a regression, never an accepted cost.

### 3. Slice code review

Run the code-review skill on the working diff (uncommitted changes, plus any commits this
slice has already made on the branch — `git diff main...HEAD` if the slice spans commits).

Triage findings:
- **Fix now:** correctness bugs, silent failures, authority-boundary violations, anything
  CRITICAL/HIGH.
- **Defer:** style/structure improvements, latent issues with no current trigger. Each
  deferred item gets a one-line entry with rationale (step 5).
- **Owner question:** anything that is a design decision, not a defect — HALT and ask.

If fixes were applied, re-run the gate.

### 4. Commit the slice

Use the Bash tool with a heredoc for the message (never PowerShell here-strings):

```
git add <files>   # add the slice's files explicitly; never git add -A blindly
git commit -m "$(cat <<'EOF'
<type>(<area>): <slice summary>

<what and why, briefly>

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

### 5. Record in PROJECT_INDEX

Update `spec/PROJECT_INDEX.md`:
- Mark the slice done in the current phase's status/START HERE section.
- Append deferred review findings to the backlog with rationale.
- Note the next slice up, so `/next-slice` in a fresh session can orient without help.

Commit the docs change separately (`docs: PROJECT_INDEX — <slice> done; next up <next>`).

### 6. Hand back

Report in one short block: gate results (test count), review outcome (N fixed / N
deferred), commit hashes, and the next slice. End with: **safe to `/clear`**.

## Notes

- Never mark the slice done if the gate is red or the review left unfixed CRITICAL items.
- Do not start the next slice in this session — fresh context per slice is the rule.
- Push the branch (`git push`) so work is not stranded locally, but never open a PR here —
  that is `/end-phase`.
