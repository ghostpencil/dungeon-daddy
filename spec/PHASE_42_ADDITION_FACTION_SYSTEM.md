# Phase 43 — Faction System

**Status:** PLANNED

Implement a first-class Faction system: a dedicated data model, live reputation tracking in
Play mode, and a faction-specific authoring UI in Campaign mode.

---

## Motivation

Factions are not actors. They don't roll dice, accumulate stress, or die. They are political
and social forces: groups that NPCs, monsters, and party members belong to, with goals of
their own and an attitude toward the party. The current `ActorManifest` model is the wrong
shape, and factions have no live presence in Play mode at all.

The Charge RPG faction model provides the guidance: track faction Goals (via clocks) and
Reputation (their attitude toward the party on a five-tier scale). Reputation changes result
from player actions — directly via LLM proposal or indirectly when faction clocks complete.

---

## Data Model

### `FactionManifest` (campaign/manifest.py)

Replaces `list[ActorManifest]` for `CampaignManifest.factions`.

```python
class FactionManifest(BaseModel):
    slug: str
    display_name: str
    concept: str | None = None
    goal: str | None = None   # what the faction is actively pursuing
    status: Literal["active", "inactive", "dissolved"] = "active"
    reputation: Literal["hostile", "cold", "neutral", "warm", "allied"] = "neutral"
    tier: int = 0             # relative power 0–4
    tags: list[str] = Field(default_factory=list)
```

`ActorManifest.actor_type` literal is updated to remove `"faction"` — factions are no
longer represented as actors anywhere in the stack.

### `FactionState` (rpg/models.py)

Runtime mirror of `FactionManifest`, persisted to DuckDB.

```python
class FactionState(BaseModel):
    faction_id: str
    campaign_id: str
    slug: str
    display_name: str
    concept: str | None = None
    goal: str | None = None
    status: Literal["active", "inactive", "dissolved"] = "active"
    reputation: Literal["hostile", "cold", "neutral", "warm", "allied"] = "neutral"
    tier: int = 0
    tags: list[str] = Field(default_factory=list)
```

---

## Reputation Tier Model

Five named tiers (ordered worst→best):

| Tier | Display | Chip color |
|------|---------|-----------|
| `hostile` | HOSTILE | EMBER |
| `cold` | COLD | INK_3 |
| `neutral` | NEUTRAL | INK_3 |
| `warm` | WARM | TEAL |
| `allied` | ALLIED | GOLD |

Tier ordering is fixed: `["hostile", "cold", "neutral", "warm", "allied"]`. Changes are
expressed as integer steps along this sequence (e.g. `delta_steps=+1` moves `cold`→`neutral`).
The applier clamps to the endpoints.

---

## Faction Power Tier (0–4)

| Value | Label |
|-------|-------|
| 0 | Fringe |
| 1 | Established |
| 2 | Influential |
| 3 | Powerful |
| 4 | Dominant |

Stored as `INTEGER` in DB and shown as a label in the UI. Not mechanically active yet —
GM reference and LLM context only.

---

## How Reputation Changes in Play

### Indirect — via faction clocks

`ClockManifest` / `ClockState` already support `clock_level="faction"` and
`owner_actor_id`. These clocks advance via the existing `compute_world_reaction()` path.
When a faction clock completes, the LLM sees it in the `WorldReaction.summary_lines`
and may propose a reputation change in its narrative response.

No changes required in `world_reaction.py`.

### Direct — via LLM proposal

Add a new `ProposedChange` kind to `rpg/proposal.py`:

```python
class AdjustReputationChange(BaseModel):
    kind: Literal["adjust_reputation"] = "adjust_reputation"
    faction_slug: str
    delta_steps: int   # steps along tier scale; clamped at endpoints
    reason: str
```

The LLM may include this in its `LLMReactionProposal.proposed_changes` list. Example:

```json
{
  "kind": "adjust_reputation",
  "faction_slug": "ossuary-cult",
  "delta_steps": -1,
  "reason": "Party killed two cult members in the nave."
}
```

The validator checks that `faction_slug` exists in the campaign's known factions. The
applier shifts the `FactionState.reputation` by `delta_steps` steps, clamped at
`"hostile"` and `"allied"`, and emits a `reputation_changed` `DomainEvent`.

---

## Database Schema — Migration 007

File: `dungeon_daddy/data/migrations/007_factions.sql`

```sql
CREATE TABLE IF NOT EXISTS factions (
    faction_id   TEXT PRIMARY KEY,
    campaign_id  TEXT NOT NULL,
    slug         TEXT NOT NULL,
    display_name TEXT NOT NULL,
    concept      TEXT,
    goal         TEXT,
    status       TEXT NOT NULL DEFAULT 'active',
    reputation   TEXT NOT NULL DEFAULT 'neutral',
    tier         INTEGER NOT NULL DEFAULT 0,
    tags         TEXT NOT NULL DEFAULT '[]',
    UNIQUE(campaign_id, slug)
);
```

---

## Faction Seeding

`rpg/seed_pack.py` gains a `SeedFaction` model and `apply_seed_pack()` handles the
`factions` key. Stable `faction_id` is derived from `{campaign_slug}:{faction_slug}` via
the same SHA-256 prefix used for actors and clocks.

`CampaignManifest.factions` drives seeding on campaign load in Play mode (same pattern
as actors/clocks today).

---

## Context Bundle

`ContextBundle` (memory/models.py) gains:

```python
faction_reputations: list[dict] = Field(default_factory=list)
```

Each entry: `{"faction_id": ..., "slug": ..., "display_name": ..., "reputation": ...,
"goal": ..., "tier": ..., "status": ...}`.

`ContextBundleBuilder._fetch_faction_reputations()` loads all active factions for the
campaign from the `factions` table and adds them to the bundle. The LLM receives faction
reputation as structured context alongside clocks and mechanical state.

---

## Campaign Authoring UI

### Faction cards (center list panel)

Replace current actor card with faction-specific card:
- Name: IM Fell English `TEXT_2XL` `INK_1`
- Type chip: `FACTION` in `GOLD` (right-aligned, as today)
- Reputation chip: tier name in appropriate color (see tier table above)
- Tier label: mono `TEXT_SM` `INK_3` (e.g. "Established")
- Concept line: italic serif `TEXT_BASE` `INK_3`, one line truncated
- **No action ratings row** (current bug — removes fight/move chips from faction cards)

### Faction edit form (right panel)

Replaces actor form for the FACTIONS section. Fields:

| Field | Widget | Notes |
|-------|--------|-------|
| NAME | `UIInputText` | `display_name` |
| SLUG | `UIInputText` | mono, auto-filled |
| CONCEPT | multiline `UIInputText` | h=80, `concept` |
| GOAL | multiline `UIInputText` | h=60, `goal` |
| REPUTATION | `[-] TIER [+]` number-row | steps through tier list; displays tier name |
| TIER | `[-] n [+]` number-row | 0–4; displays tier label |

No ACTION RATINGS section. No STRESS TRACKS section.

SAVE / CANCEL buttons: same layout as actor form.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `dungeon_daddy/campaign/manifest.py` | Add `FactionManifest`; update `CampaignManifest.factions` type; remove `"faction"` from `ActorManifest.actor_type` literal |
| `dungeon_daddy/campaign/validator.py` | Validate `FactionManifest` fields (tier range, reputation literal) |
| `dungeon_daddy/rpg/models.py` | Add `FactionState` |
| `dungeon_daddy/rpg/proposal.py` | Add `AdjustReputationChange`; add to `ProposedChange` union |
| `dungeon_daddy/rpg/proposal_validator.py` | Validate `AdjustReputationChange` (slug exists, delta_steps ∈ [-4, +4]) |
| `dungeon_daddy/rpg/proposal_applier.py` | Handle `AdjustReputationChange`; emit `reputation_changed` domain event |
| `dungeon_daddy/rpg/seed_pack.py` | Add `SeedFaction` model; apply factions in `apply_seed_pack()` |
| `dungeon_daddy/data/migrations/007_factions.sql` | Create `factions` table |
| `dungeon_daddy/memory/repository.py` | Add `save_faction()`, `get_factions()`, `update_faction_reputation()` |
| `dungeon_daddy/memory/models.py` | Add `faction_reputations` field to `ContextBundle` |
| `dungeon_daddy/memory/context_bundle.py` | Add `_fetch_faction_reputations()`; include in `build()` |
| `dungeon_daddy/ui/panels/campaign_edit_panel.py` | Add faction-specific form (`_build_faction_form()`); route FACTIONS section away from actor form |
| `dungeon_daddy/views/campaign_view.py` | Use `FactionManifest` for FACTIONS section; pass correct type to edit panel |
| `examples/campaign_manifests/bone-cathedral.json` | Migrate faction entry to `FactionManifest` shape; add `goal`, `reputation`, `tier` |
| `seed_data/campaigns/*/rpg_seed.json` | Add `factions` key if/when those seed packs are extended |
| `tests/unit/campaign/test_manifest.py` | `FactionManifest` parse, validation, CampaignManifest roundtrip |
| `tests/unit/rpg/test_faction_state.py` | `FactionState` model, reputation step logic |
| `tests/unit/rpg/test_proposal_faction.py` | `AdjustReputationChange` parse, validate, apply |
| `tests/unit/memory/test_faction_repository.py` | DB migration, save/get/update faction |
| `tests/unit/memory/test_context_bundle_factions.py` | Faction reputations appear in context bundle |
| `tests/unit/ui/test_campaign_panels.py` | Faction form fields; no action ratings; reputation picker |

---

## TDD Slices

### Slice 1 — `FactionManifest` data model
**Tests first:**
- `FactionManifest` parses with defaults (`reputation="neutral"`, `tier=0`)
- `FactionManifest` rejects unknown reputation literal
- `FactionManifest` rejects tier outside 0–4
- `CampaignManifest` accepts `list[FactionManifest]` for `factions`
- `bone-cathedral.json` parses cleanly with new faction shape

**Implementation:**
- Add `FactionManifest` to `campaign/manifest.py`
- Update `CampaignManifest.factions` type annotation
- Remove `"faction"` from `ActorManifest.actor_type` literal
- Migrate `bone-cathedral.json`

---

### Slice 2 — `FactionState` + DB migration
**Tests first:**
- `FactionState` model validates
- Migration 007 creates `factions` table
- `save_faction()` inserts; re-insert is idempotent (upsert by `campaign_id+slug`)
- `get_factions(campaign_id)` returns saved factions
- `update_faction_reputation()` steps through tiers; clamps at endpoints

**Implementation:**
- Add `FactionState` to `rpg/models.py`
- Write `dungeon_daddy/data/migrations/007_factions.sql`
- Add `save_faction()`, `get_factions()`, `update_faction_reputation()` to `MemoryRepository`

---

### Slice 3 — Faction seeding from manifest
**Tests first:**
- `SeedFaction` model parses from dict
- `apply_seed_pack()` with `factions` key inserts `FactionState` rows
- Re-applying is idempotent; does not reset reputation modified at runtime
- Stable `faction_id` deterministic from `campaign_slug:faction_slug`

**Implementation:**
- Add `SeedFaction` to `rpg/seed_pack.py`
- Extend `apply_seed_pack()` to handle factions
- Hook into Play mode campaign load path (same location as actor/clock seeding)

---

### Slice 4 — `AdjustReputationChange` in proposal system
**Tests first:**
- `AdjustReputationChange` parses from JSON with discriminator
- `validate_proposal()` rejects unknown `faction_slug`
- `validate_proposal()` accepts valid slug with known faction set
- `apply_low_risk_proposals()` calls `update_faction_reputation()` on accepted changes
- Applied change emits `reputation_changed` domain event
- Clamping: `warm + 3 steps = allied` (not overflow)

**Implementation:**
- Add `AdjustReputationChange` to `rpg/proposal.py`; add to `ProposedChange` union
- Update `validate_proposal()` signature to accept `known_faction_slugs: set[str] | None`
- Handle in `proposal_applier.py`

---

### Slice 5 — Faction reputations in context bundle
**Tests first:**
- `ContextBundle` has `faction_reputations` field (defaults to `[]`)
- `ContextBundleBuilder.build()` calls `_fetch_faction_reputations()`
- Returns list of dicts with required keys: `slug`, `display_name`, `reputation`, `goal`, `tier`
- Only `status="active"` factions are included

**Implementation:**
- Add `faction_reputations` to `ContextBundle` in `memory/models.py`
- Add `_fetch_faction_reputations()` to `ContextBundleBuilder`
- Call in `build()`

---

### Slice 6 — Campaign UI: faction edit form
**Tests first:**
- `CampaignEditPanel` routes FACTIONS section to `_build_faction_form()`, not actor form
- Faction form has NAME, SLUG, CONCEPT, GOAL widgets
- Faction form has REPUTATION `[-] tier [+]` picker (steps through tier list)
- Faction form has TIER `[-] n [+]` picker (0–4)
- Faction form does NOT contain ACTION RATINGS or STRESS TRACKS sections
- `_collect_faction_inputs()` returns a `FactionManifest`-compatible dict

**Implementation:**
- Add `show_faction()` / `_build_faction_form()` / `_collect_faction_inputs()` to `CampaignEditPanel`
- Add reputation tier stepping logic (list index arithmetic, clamped)
- Update `campaign_view.py` to call `show_faction()` for FACTIONS section items

---

### Slice 7 — Campaign UI: faction card display
**Tests first:**
- `CampaignListPanel._draw_faction_card()` renders reputation chip in correct color
- Faction cards do not render action ratings row
- Tier label appears as mono text

**Implementation:**
- Add `_draw_faction_card()` to `CampaignListPanel` (or equivalent in `campaign_view.py`)
- Route FACTIONS section card rendering to faction card path

---

## Exit Criteria

- [ ] `pytest tests/` — all passing (no regression)
- [ ] `FactionManifest` roundtrips through JSON cleanly
- [ ] `bone-cathedral.json` loads without error; faction shows in FACTIONS panel
- [ ] Faction edit form: REPUTATION and TIER pickers work; ACTION RATINGS absent
- [ ] Faction reputation persists to DuckDB on SAVE
- [ ] Context bundle includes faction reputations (verify via debug bundle display in Play mode)
- [ ] `AdjustReputationChange` accepted in proposal; `update_faction_reputation()` called
- [ ] Domain event `reputation_changed` appears in event log after proposal applied
- [ ] Clamping: no reputation can go below `hostile` or above `allied`

---

## Migration Note — bone-cathedral.json

Current faction entry shape (ActorManifest):
```json
{
  "slug": "ossuary-cult",
  "display_name": "The Ossuary Cult",
  "actor_type": "faction",
  "concept": "Scattered remnants of the cult. Still loyal to the Warden's rite.",
  "status": "active",
  "action_ratings": {},
  "stress_tracks": [],
  "tags": ["antagonist"]
}
```

New shape (FactionManifest):
```json
{
  "slug": "ossuary-cult",
  "display_name": "The Ossuary Cult",
  "concept": "Scattered remnants of the cult. Still loyal to the Warden's rite.",
  "goal": "Complete the Warden's rite and seal the relic before the party can retrieve it.",
  "status": "active",
  "reputation": "cold",
  "tier": 1,
  "tags": ["antagonist"]
}
```
