# Balance Notes — Phase 32

## Action Rating Curve

Action ratings run 0–3, translating directly to dice in the pool (minimum pool clamped to 1 in `dice.py`).

Outcome probabilities per rating:

| Rating | Dice | Miss | Partial (4–5) | Full (6) | Crit (2+ sixes) |
|--------|------|------|---------------|----------|-----------------|
| 0      | 1    | 50%  | 33%           | 17%      | 0%              |
| 1      | 2    | 25%  | 44%           | 28%      | 3%              |
| 2      | 3    | 13%  | 45%           | 35%      | 7%              |
| 3      | 4    | 6%   | 42%           | 39%      | 13%             |

**Verdict:** Healthy curve. Rating 0 stays meaningful — 50% non-miss with 1 die is a credible contributor. Rating 3 (4 dice, 94% success rate) feels powerful without being automatic. Each step from 0→1→2→3 produces a tangible improvement. No constant changes needed.

**Push yourself (+1 die, +1 stress):** For rating 0, push converts miss odds from 50% to 25% — a strong effect worth 25% of a stress track. Appropriately tempting. No change.

**Momentum spend (+1 die per point):** Follows the same per-die probability ladder as push. Each point is worth roughly the same expected improvement as gaining one rating step. Appropriate — see Momentum section below for the tracking gap.

---

## Momentum

**Gap:** Momentum is not tracked. `ActorState` has no `momentum` field; `ActionRequest.momentum_spend` accepts any integer without deduction or cap enforcement. The spec (RPG_SYSTEM_SPEC.md) calls for a cap of 6 and per-spend deduction.

**Impact now:** The GM can declare any spend freely, which works for solo or prototype play. There is no hoarding concern because there is nothing to hoard.

**Verdict:** Cap enforcement requires adding a `momentum: int = 0` field to `ActorState`, a DB migration, and deduction logic in `resolve_action`. This is architecture work outside stabilization scope.

**Deferred to Phase 33.** Phase 33 should implement: `ActorState.momentum` (int, 0–6), cap enforcement in `resolve_action`, and momentum gain triggers on critical outcomes.

---

## Stress Track Capacity

PC tracks use capacity=4 (`_DEFAULT_CAPACITY` in `stress.py`). The design intent: 4 hits fills a track, triggering fallout evaluation. With `push_yourself` costing 1 stress:

- Pushing once is 25% of a track — steep but not punishing per action
- Four pushes or accumulated hits fills the track — meaningful accumulation pace
- Mid-dungeon stress is story-relevant without being relentless

**Verdict:** Capacity 4 is appropriate. No change.

**Constant alignment fix applied:** `StressTrack.capacity` default in `models.py` was 6 (mismatched fallback). Changed to 4 to match `_DEFAULT_CAPACITY`. This prevents any code that constructs `StressTrack` without an explicit capacity from silently getting the wrong value.

---

## Fallout Severity Thresholds

Severity escalates by count of active fallout on the same track:

| Active fallout on track | Severity granted |
|-------------------------|------------------|
| 0                        | minor            |
| 1                        | moderate         |
| 2+                       | severe           |

First fill of any track is always minor. Severity escalates only if the character has not resolved prior fallout. This is fiction-first and appropriate — it encourages resolution before re-filling.

**Minor fallout catalog:** "Battered", "Rattled", "Distant", "Touched" — all suggest story hooks rather than mechanical penalties. Fits the design goal.

**Severe fallout catalog:** "Broken", "Broken Down", "Severed", "Claimed" — weighty but survivable with group support. Fits the design goal.

**Verdict:** Thresholds are correct. No change.

---

## Weird Stress

Weird has the same capacity (4) as other tracks. Its distinctiveness comes from:

- `fallout.py`: `evaluate_fallout` attaches `dungeon_influence: True` and `write_memory: True` hooks to all Weird fallout records
- `apply_intimacy_risk`: accepting dungeon comfort costs 1 Weird stress and adds vulnerability tags
- Recovery fiction: the spec requires Weird recovery to "rarely be clean" — the system supports this via fiction (GM enforcement), not mechanical locks

**Max Weird ("Claimed"):** "Part of you belongs to the dungeon now. It speaks through your silence." — This is catastrophic in fiction and should feel so. The hook-writing ensures it surfaces in context bundles and DM prompts.

**Verdict:** Risk/reward balance is appropriate. Weird is the only track that leaves persistent dungeon knowledge tags on the actor. The temptation comes from `Channel` action utility, visions, and dungeon-powered abilities — not mechanical incentives to take Weird hits. No change.

---

## Summary of Changes

| Item | Action |
|------|--------|
| `StressTrack.capacity` default | Changed 6 → 4 in `models.py` |
| Momentum tracking | Deferred to Phase 33 |
| All other constants | Confirmed correct, no change |
