# End Phase

Close out the phase: gate → owner UI review → PR → whole-arc review → merge approval →
bookkeeping. Halts exactly twice: UI review and merge approval. Process reference:
`spec/SDLC.md`.

## How to use

`/end-phase` — after the last slice of the phase has been through `/end-slice`.

## Workflow

### 1. Preconditions

- Read `spec/PROJECT_INDEX.md`; confirm every slice of the phase is marked done. If not,
  say which is open and stop — finish it via `/next-slice` + `/end-slice` first.
- On the phase branch, working tree clean, branch pushed.

### 2. Run the gate

```
python -m ruff check .
python -m mypy dungeon_daddy
python -m pytest -q
```

Also run whatever phase-level verification the phase spec calls for (smoke test,
UI-harness tests — read `spec/UI_TESTING.md` only if so). Fix and re-run until green.

### 3. Owner UI review — HALT

Tell the owner the phase is gate-green and ready for their UI pass. List what to look at:
the phase's user-visible behaviors from the spec's exit criteria, plus anything the live
Crucible save needs (reseed gotchas are in PROJECT_INDEX). The owner drives the app
themselves (`python -m dungeon_daddy`) — do not drive it with computer-use.

Findings become fix commits (through the gate again). Large findings mean a new slice —
stop and say so. Proceed only on explicit owner OK.

### 4. Open the PR

```
gh pr create --title "<Phase NN — title>" --body "$(cat <<'EOF'
## Summary
<phase summary against its exit criteria, slice by slice>

## Test plan
<gate results, smoke/UI-harness coverage, owner UI review done>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 5. Whole-arc review

Run `pr-review-toolkit:review-pr` on the PR. Apply fix batches, re-run the gate, push,
and update the PR body with what changed. If the phase was large or high-risk, suggest
`/code-review ultra <PR#>` to the owner as an optional deeper pass (owner-triggered, paid).

Owner-facing design questions found by review HALT — they go to the owner, not into the
fix batch.

### 6. Merge approval — HALT

Present: PR link, review outcome (N fixed / N deferred-to-backlog), final gate results,
CI status (`gh pr checks`). Ask for merge approval. On approval:

```
gh pr merge <PR#> --merge
git checkout main && git pull
```

### 7. Post-merge bookkeeping (on main)

- `spec/PROJECT_INDEX.md`: add the Phase History row, flip the Phase section to the next
  state (next phase or STABILIZATION), fold deferred review findings into the backlog,
  refresh START HERE.
- Trim/align the phase spec if the review changed behavior described there.
- Commit directly to `main` (`docs: PROJECT_INDEX — Phase NN merged; next up <next>`).
- Suggest any durable lessons worth saving to auto-memory.

## Notes

- Never merge with a red gate or failing CI; branch protection requires the `test` check.
- Deferred findings go to the PROJECT_INDEX backlog, not silently dropped — a big pile is
  grounds to propose a cleanup slice at the next phase-scope decision.
