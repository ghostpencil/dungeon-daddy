# Phase 49 — Starting Playbooks: Class Foundations (Verbs + Adverbs)

**Status: COMPLETE** — implemented 2026-06-19; all 7 slices (0–6) done; 57 new tests; 2867 total
passing. Branch: `phase-49`. Committed `94c5fcb`.
GitHub issue: [#77](https://github.com/ghostpencil/dungeon-daddy/issues/77) (label `phase-49`).
Sourced from `ghostpencil/dungeon-daddy` Project #1 card "Phase 49: Starting Playbooks —
Class Foundations (Verbs + Adverbs)".
Depends on: Phase 46 (Inventory / Class Kits) — complete. Phase 48 — complete.

**Post-implementation decision:** each playbook grants its kit ability **and its first pool
ability** as starting abilities; the remaining `ability_pool` entries are locked until Phase 52
milestones. `starting_abilities` in `data/playbooks.json` reflects this (two slugs each).
The seeder already handled pool entries in `starting_abilities` via `source="playbook_start"`.

> This is the start-of-phase reconciliation spec. It targets the full scope from the Project #1
> card, with the codebase as-built and the 2026-06-17 design review folded in as locked
> decisions. Where the card and the as-built code disagree, the code/review wins — same rule as
> the Phase 47/48 specs.

## Goal

Add **playbooks** — character classes defined at creation. A playbook is bundled, read-only
data (like `loop_patterns.json`) that, when an actor is created from it, populates: starting
**action ratings**, **stress tracks**, a **class kit**, **starting abilities**, class **tags**,
and **signature adverbs**. The phase also adds the durable record of which abilities an actor
*currently holds* (`actor_abilities`), so the Phase 50 action picker can read a live verb/adverb
set.

This is **Part 1** of the former "Playbooks" phase — the *starting* playbook only.
Milestone advancement (beats, ranks-to-5, unlockable abilities) is **Phase 52**. The schema
defines `beats` and `ability_pool` here; they are only *wired up* in Phase 52.

## Why this comes before the Action Model (Phase 50)

Phase 50's action picker reads two playbook-derived sets per actor:

- **Verbs** = the 9 universal verbs (filtered by room context + playbook gates) ∪ **class verbs**
  (the actor's abilities — `active_stress` abilities surface as standalone verbs; kit abilities
  gate universal verbs).
- **Adverbs** = the universal adverb pool (filtered by target type + world state) ∪ the
  playbook's **signature adverbs**.

So Phase 50 has no real Verb/Adverb input until playbooks exist. The picker will read the
actor's **live** `actor_abilities`, so Phase 52 advancement grows the lists with no rewiring.

## Locked design decisions

These reconcile the card with the codebase as-built and the 2026-06-17 design review. They take
precedence over the card body where they conflict.

1. **9 universal verbs, not class-owned (Gap 9).** Per `RPG_SYSTEM_SPEC.md` the action list is
   `fight, move, tinker, study, focus, sway, sense, channel, endure`. A playbook does **not**
   own a verb exclusively. The card's "Signature verbs" column marks a class's *emphasis* only;
   it is descriptive, not a data field. `endure` is universal, not Fighter-only.

2. **A playbook's unique mechanical contribution is its signature adverbs + kit/abilities** —
   not exclusive verbs. Ratings/tracks/kit are *starting values*, not class locks.

3. **Playbooks are bundled, read-only JSON** under `dungeon_daddy/data/` (mirroring
   `loop_patterns.json` + its loader in `data/models.py`). Reusable across all campaigns; not
   per-campaign manifest data.

4. **`actor_abilities` is a new, richer table — it supersedes the dormant `abilities` table.**
   The legacy `abilities (actor_id, ability_key, value)` table from
   `001_rpg_memory_foundation.sql` has **no Python reader or writer** (verified: no `FROM
   abilities` / `INTO abilities` anywhere). Per the card we add `actor_abilities` carrying the
   verb-rendering structure (surfaces-as-verb, accepted target types, cost). The dormant
   `abilities` table is left in place (no destructive migration) but is considered superseded;
   nothing new writes to it (confirmed: decision R1 below).

5. **Character creation is rigid (no customisation) this phase.** Pick a playbook → ratings,
   tracks, kit, tags, signature adverbs, starting abilities auto-populate → review/confirm →
   actor written to `CampaignManifest` with `playbook_slug`. Per-point buy / swapping is out of
   scope (a possible later phase).

6. **`ActorManifest` / `ActorState` grow additively.** Add `playbook_slug: str | None = None`
   to both (and the `actors` table). Existing seeded actors with no playbook keep working
   (`None`). The existing `ActorManifest.action_ratings` / `stress_tracks` / `tags` fields are
   the population *target* — applying a playbook fills them; it does not introduce a parallel
   path. Signature adverbs + starting abilities are the genuinely new seeded data.

7. **Preserve existing saves.** Migration `011_*` is additive (new `actor_abilities` table +
   `actors.playbook_slug` column). Pre-Phase-49 campaigns load unchanged with no playbook and an
   empty ability set. No backfill is required for old saves to keep running; a Phase-49 actor
   only gains data when re-published from a manifest that names a playbook.

## Data model

### Bundled playbook JSON — `dungeon_daddy/data/playbooks.json`

New Pydantic models in a new `rpg/playbook.py` module (decision R2):

```python
class PlaybookStressTrack(BaseModel):
    track_key: str            # body | composure | bonds | weird
    capacity: int = 4         # PC tracks are 4 per BALANCE_NOTES.md (card's 6 is superseded)

class SignatureAdverb(BaseModel):
    slug: str                 # e.g. "silently"
    target_types: list[str]   # subset of: npc | object | item | room | self | monster

class PlaybookAbility(BaseModel):
    slug: str
    display_name: str
    description: str
    surfaces_as_verb: bool = False     # standalone pickable verb in Phase 50?
    target_types: list[str] = []       # accepted nouns when surfaced
    cost_type: Literal["none", "active_stress", "momentum"] = "none"
    cost_amount: int = 0

class PlaybookKit(BaseModel):          # maps onto the Phase 46 class_kit Item
    slug: str
    display_name: str
    description: str
    charges_max: int
    abilities: list[PlaybookAbility] = []   # kit-granted abilities

class Playbook(BaseModel):
    slug: str
    display_name: str
    starting_action_ratings: dict[str, int]          # action_key -> 0..3
    starting_stress_tracks: list[PlaybookStressTrack]
    starting_kit: PlaybookKit
    tags: list[str]                                  # class/background tags
    signature_adverbs: list[SignatureAdverb]
    starting_abilities: list[str]                    # slugs, granted at publish
    ability_pool: list[PlaybookAbility] = []         # Phase 52 (defined, not wired)
    beats: list[dict] = []                           # Phase 52 (defined, not wired)
```

Validation: action keys ∈ the 9 universal verbs; ratings 0–3; track keys ∈
`{body, composure, bonds, weird}`; `starting_abilities` slugs must resolve within the kit
abilities ∪ `ability_pool`; slugs unique; adverb `target_types` from the controlled set.

### `actor_abilities` table (migration `011`)

```sql
CREATE TABLE IF NOT EXISTS actor_abilities (
    actor_id        TEXT NOT NULL,
    ability_slug    TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    description     TEXT NOT NULL,
    source          TEXT NOT NULL,           -- 'playbook_start' | 'kit' | (Phase 52: 'advancement')
    surfaces_as_verb BOOLEAN NOT NULL DEFAULT FALSE,
    target_types    TEXT NOT NULL DEFAULT '[]',  -- JSON array
    cost_type       TEXT NOT NULL DEFAULT 'none',
    cost_amount     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (actor_id, ability_slug)
);
ALTER TABLE actors ADD COLUMN playbook_slug TEXT;  -- nullable
```

Repo CRUD: `save_actor_ability(...)`, `get_actor_abilities(actor_id) -> list[ActorAbility]`,
`delete_actor_ability(actor_id, slug)`. Mirror the existing `get_items` / `save_actor_*`
patterns in the repo.

### `PlaybookLibrary`

A loader paralleling the loop-pattern loader: `load() -> dict[str, Playbook]`, `list()`,
`get(slug) -> Playbook`. Reads bundled `data/playbooks.json` via `pathlib`. Read-only.

### Manifest + model additions

- `ActorManifest.playbook_slug: str | None = None` (`campaign/manifest.py`).
- `ActorState.playbook_slug: str | None = None` (`rpg/models.py`).
- `ActorManifest.signature_adverbs` / starting-ability data are **not** duplicated on the
  manifest or the actor — they are derived live from the playbook via `playbook_slug` (single
  source of truth; decision R3). Only abilities persist (in `actor_abilities`).

## Bundled playbooks (initial set)

Covers The Crucible party. Signature verbs are emphasis only (not a field).

| Playbook  | Kit            | Emphasis verbs   | Signature adverbs                  |
|-----------|----------------|------------------|------------------------------------|
| Fighter   | Combat Gear    | fight, endure    | recklessly, brutally, with discipline |
| Thief     | Thieves' Tools | move, tinker     | silently, deftly, unseen           |
| Priest    | Holy Kit       | channel, study   | reverently, austerely              |
| Artificer | Workshop Kit   | tinker, focus    | precisely, experimentally          |

## Seed / publish wiring

At publish (`campaign/seeder.py` `_seed_actor` + `campaign/publish.py`):

1. If `actor.playbook_slug` is set, load the playbook via `PlaybookLibrary`.
2. Apply starting ratings / stress tracks (fill the actor's `action_ratings` / `stress_tracks`
   if the manifest left them empty; the rigid creation UI will pre-fill them so publish is a
   straight write).
3. Seed the class kit as a Phase-46 `class_kit` `Item` owned by the actor (reuse `_seed_item`
   path — do **not** fork a second kit-seeding code path).
4. Write `actors.playbook_slug`.
5. Write `starting_abilities` (+ kit abilities) into `actor_abilities` with `source`.
6. Add class `tags` to the actor's tags.

Idempotency / `--force` semantics must match the existing actor/item seeding (see `_seed_actor`,
`_seed_item`): re-publish replaces, dry-run reports without writing.

## UI

- **Character creation in the Seed editor** (`ui/panels/campaign_edit_panel.py`,
  `show_actor` / `_build_actor_form`): add a **playbook picker**. Selecting a playbook
  auto-populates the actor form (ratings, tracks, tags, signature adverbs, starting abilities)
  read-only/confirm — rigid, no per-field editing this phase. Roundtrip `playbook_slug` through
  the existing `_extra_data` mechanism (same approach used for `actor_type`).
- **Character Sheet panel** (`ui/panels/character_sheet_panel.py`): show playbook name, tags,
  signature adverbs, and starting abilities. Beats/advancement view is deferred to Phase 52.

## Folded-in bug fix — party marker lost when browsing levels (Phase 48 navigation)

> **Not a playbook concern** — this is a Phase 48 dungeon-navigation bug, tracked here at the
> user's request (2026-06-19) and scheduled as **Slice 0** (do before the playbook slices).
> Status: documented, **not yet built**.

**Symptom.** In Play mode, with the party in a room on Level 1: page the map to Level 2 with the
▲▼ level-stepper arrows, then page back to Level 1 — the gold party-location marker is gone for
good.

**Root cause.** Two code paths change "the level," and the browse path corrupts party state:
- *Real movement* goes through `apply_move_party` (the `MoveParty` command / connector path,
  `play_view.py:987`) — authoritative, correct.
- *The ▲▼ stepper* (`_on_level_change`, `play_view.py:1296`) is meant to be a **view-only map
  browser** but writes the party's canonical fields directly:
  ```python
  self._state.current_level_idx = new_idx     # mutates the PARTY's level
  self._state.current_room_id = None          # wipes the party's room — marker lost
  ```
  Browsing therefore overwrites party location. The map draw (`map_panel.py:424`) renders
  `party_room_id=current_room_id`, which is now `None`.

This **violates the Phase 48 locked decision** that the engine is the *sole writer* of
`current_room_id` / `current_level_idx` (only via validated commands). The stepper is a leftover
that writes them directly.

**Fix (separate viewed-level from party-level).**
- Add a map-browser **`viewed_level_idx`** (on the map panel or play view) independent of the
  session's `current_level_idx` (which stays the party's authoritative level).
- The ▲▼ arrows change `viewed_level_idx` only — they must **not** touch `current_level_idx` or
  `current_room_id`.
- Draw the party marker only when `viewed_level_idx == party_level_idx`; pass `party_room_id`
  only on that level (otherwise `None`).
- When the party actually moves levels via `MoveParty`/connector, the viewed level follows the
  party (sync `viewed_level_idx` to the new `current_level_idx`).

**TDD.** Behavior test: browse away from and back to the party's level → `current_room_id` is
unchanged and the marker re-renders; browsing to a non-party level passes `party_room_id=None`
to the renderer. (Read `spec/UI_TESTING.md` / `spec/TESTING.md` first.)

## Slice plan (TDD)

Each slice is one behavior, tests first. Read `spec/TESTING.md` and invoke the TDD skill before
each new test file (per CLAUDE.md).

0. ✅ **Bug fix — party marker survives level browsing** (Phase 48 navigation). View-only
   `viewed_level_idx`; stepper no longer mutates party location; marker gated to the party's level.
1. ✅ **Playbook schema (Pydantic).** `Playbook` + nested models with validation. 11 tests.
2. ✅ **`PlaybookLibrary`.** Bundled `data/playbooks.json`; `list()` / `get(slug)`. 7 tests.
3. ✅ **`actor_abilities` schema + repo CRUD** (migration `011`). 8 tests.
4. ✅ **Seed-publish wiring.** `_seed_actor` applies playbook: ratings/tracks/tags, kit Item,
   `playbook_slug`, `actor_abilities` rows. 9 tests.
5. ✅ **Character creation UI** — playbook picker in Seed editor. 12 tests.
6. ✅ **Character Sheet panel** — PLAYBOOK / ADVERBS / ABILITIES sections. 10 tests.

Slice 0 is an independent Phase-48 navigation bug fix (folded in by request); it can land on
its own or first on the phase branch. Slices 1–4 are the engine/data spine (the Phase-50-enabling
deliverable). Slices 5–6 are UI and could be split to a follow-up if the spine needs to land first.

## Resolved decisions (was: open questions) — settled 2026-06-19

- **R1 (was O1) — RESOLVED: new table.** Add a new `actor_abilities` table; leave the dormant
  `abilities` table untouched (no destructive migration). Nothing new writes to `abilities`.
- **R2 (was O2) — RESOLVED: new module.** `Playbook`, the nested models, and `PlaybookLibrary`
  live in a new `rpg/playbook.py` (loader near model, mirroring loop patterns). `ActorState`
  keeps its additive `playbook_slug` field in `rpg/models.py`.
- **R3 (was O3) — RESOLVED: derived-live.** Signature adverbs are **not** persisted per-actor;
  they are read live from the playbook via the actor's `playbook_slug`. Only **abilities**
  persist (in `actor_abilities`), because Phase 52 mutates the held set. The Character Sheet and
  Phase 50 picker resolve adverbs through `PlaybookLibrary.get(actor.playbook_slug)`.
- **R4 (was O4) — RESOLVED via `BALANCE_NOTES.md`:**
  - **Stress capacity = 4, not 6.** `BALANCE_NOTES.md` fixes PC track capacity at 4
    (`_DEFAULT_CAPACITY` in `stress.py`; the `StressTrack.capacity` default was deliberately
    changed 6→4 to kill a mismatch). The card's example JSON (`body` capacity 6) is **superseded**
    — `PlaybookStressTrack.capacity` defaults to **4**, and bundled playbooks use 4 for every PC
    track unless a future balance pass justifies otherwise. Model `capacity: int = 4` already
    matches; validation should reject capacities that diverge without a documented reason.
  - **Ratings 0–3, and 0 is meaningful.** The rating curve (1 die at rating 0 = 50% non-miss)
    means a playbook may legitimately leave several actions at 0; emphasis verbs sit at 2,
    secondary at 1. First-pass bundled spread: two emphasis verbs at **2**, one or two support
    actions at **1**, the rest **0** (kept modest so Phase 52 advancement has room to climb).
  - **Momentum cost abilities are schema-only.** `cost_type="momentum"` is accepted in the model
    but momentum is still untracked (`BALANCE_NOTES.md` defers it; `ActorState` has no `momentum`
    field). Bundled starting abilities should avoid `momentum` cost for now; `active_stress` and
    `none` are the live cost types this phase.
  - Exact kit `charges_max` and ability prose are drafted in Slice 2 and reviewed against the
    Phase-46 kit conventions before locking.

## Out of scope (Phase 52 or later)

- Beats, milestone detection, `FulfillMilestone`, ranks-to-5, ability-pool unlocks.
- Point-buy / custom character creation; multiclassing.
- Wiring abilities into the action roll (that is Phase 50's picker + resolution).

## Exit criteria

- [x] Four bundled playbooks load and validate via `PlaybookLibrary`.
- [x] Publishing a campaign whose actor names a `playbook_slug` seeds ratings, tracks, kit Item,
  tags, `playbook_slug`, and `actor_abilities` rows — idempotently.
- [x] Pre-Phase-49 saves load unchanged (no playbook, empty ability set).
- [x] Seed editor can create an actor from a playbook (rigid auto-populate); Character Sheet shows
  playbook, tags, signature adverbs, starting abilities.
- [x] Full suite green (2867 passing); new behavior covered by tests written test-first.
