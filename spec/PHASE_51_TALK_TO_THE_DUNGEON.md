# Phase 51 — Talk to the Dungeon

**Status:** ✅ **SPEC FINALIZED — ready to implement** (decisions locked 2026-06-26). Not started.
Branch `phase-51`.
**Type:** BUILD (roadmap phase; GitHub Projects `ghostpencil/dungeon-daddy` #1).
**Depends on:** Phase 50 (Hybrid Action Model), Phase 50.6 (Chat Action Cockpit — carved the
SAY/ASK input seam: `ChatPanel.set_dialogue_mode`, `_begin_dialogue_stub`/`_on_dialogue_send_stub`,
the `_dialogue_stub_active` routing flag, and `creature disposition`).
**Roadmap one-liner:** *Intimacy-gated freeform channel at resonance points.*

> **Authority boundary (non-negotiable, `docs/LLM_AUTHORITY_BOUNDARY.md`):** the dungeon channel is
> the *one* place in play mode where freeform LLM output is fully appropriate — **there are no
> mechanics to resolve, only narration.** The LLM plays the dungeon's voice. It **may** narrate,
> deflect, lie, and ask questions back; it **may not** advance clocks, apply stress, create
> authoritative memory, mutate state, or bypass validation. The **engine** ticks the intimacy clock
> and writes memory drafts — never the LLM.

---

## 1. Problem / Opportunity

Phase 50.6 carved a SAY/ASK input seam but left it stubbed: typing into the dialogue box echoes the
line and immediately ends the "conversation." Two conversational surfaces are implied but unbuilt:

1. **The dungeon channel** (this phase's canonical scope) — a freeform conversation between the
   player and *the dungeon itself*: an ancient, interested, dangerous presence with a personality
   voice defined in the seed. What it reveals, withholds, or distorts **deepens with intimacy**, and
   the relationship cuts both ways.
2. **NPC dialogue** (the 50.6 `sway → willing creature` stub) — talking to a *willing* NPC/monster
   noun. This is a *sibling* surface that reuses the same SAY-box plumbing. See **§3 D1** for how
   this phase treats it.

This is the right moment because: (a) the input seam, dialogue-mode swap, and `disposition` gate
already exist; (b) the LLM provider + `DungeonMasterAgent` + context-bundle infrastructure is mature;
(c) the `current_room` context bundle already carries a `resonance_point` flag (partial plumbing).

## 2. Goal

> Standing at a **resonance point**, with the **dungeon intimacy clock** above threshold, the player
> opens a visually-distinct **Talk to the Dungeon** channel, types freely, and the dungeon answers in
> its seed-defined voice — cryptic when intimacy is low, personal and manipulative when high. Each
> exchange **advances the intimacy clock** (engine-applied) and **drafts a memory** of what was said.
> The dungeon may lie. Talking is never purely safe.

Two gates, both must pass for the channel to be active:
- **Location gate** — the current room is a **resonance point** (seed-marked).
- **Intimacy gate** — a `dungeon_intimacy` clock exists and its `filled/segments` ≥ a threshold.

---

## 3. Decisions locked (2026-06-26)

Confirmed with the product owner before Slice 1. Chosen option in **bold**.

| # | Decision | Resolution |
|---|---|---|
| **D1** | **NPC dialogue vs. dungeon channel scope** | **(a) Shared dialogue engine; deliver the dungeon channel fully; fold the 50.6 NPC `sway→willing` stub onto it.** `_on_dialogue_send` dispatches by `DialogueSession.kind` (`"dungeon"` / `"npc"`); `dungeon` fully implemented, `npc` wired as a thin binding (the stub already swaps surfaces). |
| **D2** | **How the dungeon channel is *entered*** | **New `resonance_point` object archetype** (seed-author's room marker) **+ a "Speak to the Dungeon" overlay affordance** (player's button, shown only at a resonance point). The dungeon is not a creature noun, so it gets its own entry. |
| **D3** | **Intimacy clock provenance** | **Must pre-exist in the seed.** `category="dungeon_intimacy"`, `clock_level="dungeon"`, `monotonic=False`. If absent → channel locked with a clear message. No auto-creation (hides authoring intent, risks duplicates). |
| **D4** | **Memory write-back authority** | **Engine writes a `draft` `MemoryEntry`** (type `dungeon_state` or `relationship`, default importance) summarizing each exchange — never an LLM-authored authoritative write. Approval flows through the existing memory curation path. |
| **D5** | **Corruption clock (card's optional extension)** | **(a) Scaffold only** — seed flag `dungeon_corruption_clock: bool` + threshold read; **no proposal emission** this phase. Proposal-driven corruption is a marked follow-on seam. |
| **D6** | **Does a dungeon reply emit proposals?** | **No proposals in Phase 51** beyond the engine-applied intimacy tick + memory draft. The channel is pure narration; corruption-driven proposals are the D5 follow-on. Keeps the boundary clean. |

---

## 4. Design

### 4.1 Data model additions

**`CampaignManifest`** (`dungeon_daddy/campaign/manifest.py:117`) gains:
- `dungeon_voice: str | None = None` — personality description fed to the LLM
  (e.g. *"cold, industrial, analytical — speaks in diagnostics and threat assessments"*).
- `dungeon_knowledge: list[str] = []` — what the dungeon knows that the party does not (secrets,
  true motives, hidden history). A **filtered slice** is revealed, scaling with intimacy.
- `dungeon_corruption_clock: bool = False` — opt-in flag for the D5 corruption scaffold.

**`ObjectArchetype`** (`dungeon_daddy/rpg/models.py:224`) gains `"resonance_point"`. A
`RoomObject` of this archetype has no state-transition interaction — interacting **opens the
dungeon channel**. (Per D2.)

**`ClockState`** (`dungeon_daddy/rpg/models.py`) gains `monotonic: bool = True` — see §4.2.

### 4.2 Recedable intimacy clock (settled, "Gap 3")

Today's `advance_clock(clock, ticks)` (`dungeon_daddy/rpg/clocks.py`) is **monotonic**: adds ticks,
clamps to `segments`, latches `status="completed"`, never decrements. The intimacy clock must move
**both ways**, so this phase adds — **backward-compatibly**:

- A signed **`tick_clock(clock: ClockState, delta: int) -> ClockState`** — `delta` may be negative;
  result `filled` is clamped to `[0, segments]`. When `monotonic` and `filled` reaches `segments`,
  status latches `completed` (current behavior). When **not** `monotonic`, `filled` may decrease and
  status **never latches** — thresholds are read live.
- A **`monotonic: bool = True`** field on `ClockState`. **All existing clocks/seeds/tests stay green**
  (default unchanged). Intimacy/relationship clocks set `monotonic=False`.

`advance_clock` stays as-is (or becomes a thin `tick_clock(clock, +ticks)` wrapper — TBD in the
refactor slice, preserving its current signature and behavior for existing callers).

The three intimacy gate bands read `filled/segments` **live** (not a one-time completion event):
- **Below threshold** → channel locked: *"The dungeon does not yet know you well enough to speak."*
- **At threshold** → cryptic: fragments, deflection, questions back at the player.
- **High fill** → personal, targeted, manipulative — the dungeon uses what it has learned.

`completion_effect` on an intimacy clock is treated as **high-threshold behavior**, not an
irreversible fire.

### 4.3 Dialogue session state

A small in-memory `DialogueSession` (PlayView-owned, replaces the bare `_dialogue_stub_active` flag):
- `kind: Literal["dungeon", "npc"]` (per D1)
- `target_id: str | None` (NPC actor id; `None` for the dungeon)
- `room_id: str` — the resonance room the channel was opened in
- `turns: list[tuple[role, text]]` — running exchange (for the LLM history + memory summary)

Opening sets dialogue mode; leaving the resonance room, an explicit close, or a `/leave` ends it and
swaps back to the Action Builder.

### 4.4 LLM input contract (dungeon kind)

The dungeon channel builds a **dedicated dialogue bundle** (not the full DM `run_scene` bundle) and
calls the provider via a thin `DungeonVoiceAgent` (or a `mode="dungeon_voice"` path on
`DungeonMasterAgent` — TBD; both inject the `LLMProvider`, no new dependency). Input:

```
mode: dungeon_voice
dungeon_voice:      <seed dungeon_voice string>
intimacy_level:     filled / segments        (e.g. 4/6)
dungeon_knowledge:  [slice filtered by intimacy band]   (§4.5)
player_message:     <the line the player typed>
actor:              <acting actor slug>
recent_memories:    [last ~3 approved memory entries]   (via MemoryRetriever)
```

The LLM responds in the dungeon's voice — it may answer, deflect, **lie**, or ask back. It does
**not** resolve mechanics. Response is posted to chat in a **distinct dungeon bubble** (§4.6).

### 4.5 Knowledge filtering by intimacy

`dungeon_knowledge` is revealed progressively: a pure helper
`reveal_knowledge(knowledge: list[str], filled: int, segments: int) -> list[str]` returns the slice
the dungeon may draw on at the current band (e.g. none below threshold, a fragmentary head slice at
the cryptic band, the full list at high fill). Exact banding → §6 / BALANCE_NOTES.

### 4.6 UI treatment (per the card + 50.6 seam)

- The **Talk to the Dungeon** input is a **separate, visually-distinct mode** — darker palette /
  different font treatment suggesting the uncanny — reusing the SAY-box swap (`set_dialogue_mode`)
  but styled apart from the DM-chat free-text and the Action Builder.
- Dungeon responses use a **distinct bubble** separate from DM narration. The 50.6 `ChatPanel`
  already has a `"dm"`/dungeon role (violet, "◆ Dungeon"); confirm/extend its styling for this
  channel (possibly a new role to keep DM-narration and dungeon-voice visually apart).
- The channel is **only visible/active** when standing at a resonance point **and** the intimacy
  threshold is met; otherwise hidden or greyed with the lock message.

### 4.7 Engine side-effects per exchange (authoritative, not LLM)

After each dungeon reply, the **engine** (not the LLM):
1. `tick_clock(intimacy, +delta)` — talking advances intimacy (the dungeon learns about you);
   truthful answers to the dungeon's questions may advance faster (§6). Applied + persisted by
   service code, never proposed by the LLM.
2. Drafts a `MemoryEntry` (status `draft`) summarizing the exchange (per D4).

---

## 5. Non-goals

- **No mechanical resolution in-channel** — no dice, no action cards, no clocks other than the
  intimacy tick. (D6.)
- **No LLM-authored authoritative state** — memory writes are engine-made drafts; clock ticks are
  engine-applied. (Authority boundary.)
- **No corruption proposal emission** this phase — scaffold only. (D5.)
- **No new LLM library/provider** — reuse the injected `LLMProvider` / OpenAI `gpt-4o`.
- **No always-on freeform chat** — the channel is gated; the default bottom-of-column input stays the
  Action Builder (50.6 decision #2).

---

## 6. Open balance questions (→ `BALANCE_NOTES.md` when tuning)

- Intimacy threshold for "speaks coherently"; band boundaries for cryptic vs. high-fill.
- Per-exchange intimacy `+delta`; bonus for truthful answers to the dungeon's questions.
- `reveal_knowledge` banding (how much of `dungeon_knowledge` unlocks per band).
- Default `segments` for a `dungeon_intimacy` clock.

---

## 7. Slice plan (TDD — read `spec/TESTING.md` first, use the TDD skill)

Mirrors the card's 8-slice plan, re-ordered to build pure helpers/data first, UI last. Each slice is
test-first, one behavior, suite green before the next.

1. **Manifest fields** — `dungeon_voice` / `dungeon_knowledge` / `dungeon_corruption_clock` on
   `CampaignManifest`; seed validation + round-trip. *(pure model)*
2. **Recedable clock engine** — `monotonic` field on `ClockState`; signed `tick_clock(clock, delta)`
   (clamp `[0, segments]`, no-latch when non-monotonic); `advance_clock` behavior preserved for
   existing callers. *(pure rpg — the riskiest backward-compat slice; full clock/seed suite must
   stay green)*
3. **Resonance archetype** — `"resonance_point"` in `ObjectArchetype`; room context exposes the
   resonance flag end-to-end (the `current_room` bundle already has the key — wire the archetype to
   it). *(model + context)*
4. **Intimacy gate** — pure `dungeon_channel_available(room_context, intimacy_clock) -> (bool, reason)`:
   resonance AND threshold; returns the lock reason when closed. *(pure helper)*
5. **Knowledge filtering** — pure `reveal_knowledge(knowledge, filled, segments)`. *(pure helper)*
6. **Dungeon-voice bundle + agent** — build the §4.4 input bundle; `DungeonVoiceAgent`/mode that
   injects `LLMProvider` and returns the reply. Tested with a **fake provider** (per TESTING.md mock
   policy) — assert the assembled prompt carries voice/intimacy/knowledge/message, not the live API. *(LLM seam)*
7. **Engine side-effects** — per-exchange intimacy `tick_clock(+delta)` (engine-applied) + `draft`
   `MemoryEntry` write (D4). Assert clock persisted + memory drafted; assert **no** authoritative
   LLM write path is touched. *(service)*
8. **PlayView dialogue routing** — replace `_on_dialogue_send_stub` with real routing via a
   `DialogueSession` (D1 dispatch by `kind`); `_begin_dialogue` opens dungeon vs. npc; reply posted
   to the distinct bubble; leaving the room / `/leave` closes. Rebind the NPC `sway→willing` stub
   onto the shared engine (D1a). *(integration)*
9. **UI treatment** — distinct dungeon input/bubble styling; resonance-point entry affordance
   (D2b overlay button); gated visibility. Manual GUI verify per house practice; smoke test optional
   (50.6 precedent). *(UI)*
10. *(optional, D5)* **Corruption scaffold** — `dungeon_corruption_clock` definition + threshold read;
    no proposal emission. Mark the proposal seam.

> **Seeding for playtest:** add `dungeon_voice` + `dungeon_knowledge` to the Crucible seed and a
> `dungeon_intimacy` clock (`monotonic=False`) + a `resonance_point` object in a fitting room
> (a shrine/nexus/heart room). Likely `tools/populate_crucible_level*.py` + the manifest. Close the
> app first (DuckDB single-writer); migration for the new clock column applies on load.

---

## 8. Files in scope (anticipated)

| Area | File | Change |
|---|---|---|
| Manifest | `dungeon_daddy/campaign/manifest.py` | + `dungeon_voice` / `dungeon_knowledge` / `dungeon_corruption_clock` |
| Clock model | `dungeon_daddy/rpg/models.py` | + `ClockState.monotonic`; + `"resonance_point"` archetype |
| Clock engine | `dungeon_daddy/rpg/clocks.py` | + `tick_clock(clock, delta)`; preserve `advance_clock` |
| Migration | `data/migrations/0NN_clock_monotonic.sql` | + `clocks.monotonic` column (default true) |
| Helpers | `dungeon_daddy/rpg/dungeon_channel.py` *(new)* | `dungeon_channel_available`, `reveal_knowledge` |
| LLM | `dungeon_daddy/llm/agents/` | `DungeonVoiceAgent` or `dungeon_voice` mode + dialogue bundle |
| Memory | `dungeon_daddy/memory/…` | engine-side draft memory write for exchanges |
| Context | `dungeon_daddy/rpg/room_context.py` / `memory/context_bundle.py` | wire resonance archetype → flag |
| UI | `dungeon_daddy/ui/panels/chat_panel.py` | distinct dungeon input/bubble styling |
| View | `dungeon_daddy/views/play_view.py` | `DialogueSession`, real `_on_dialogue_send`, entry affordance |
| Seed | `tools/populate_crucible_level*.py` + Crucible manifest/seed | voice, knowledge, intimacy clock, resonance room |

---

## 9. Acceptance (when the phase is done)

- At a resonance room with intimacy ≥ threshold, the player opens **Talk to the Dungeon**, types,
  and gets an in-voice reply in a distinct bubble; below threshold the channel shows the lock message.
- Each exchange **advances the intimacy clock** (visibly, and it can recede over time) and leaves a
  **draft memory**.
- `dungeon_knowledge` revealed scales with intimacy band.
- The LLM never mutates authoritative state — clock + memory writes are engine-side; no proposal is
  emitted (D6).
- All pre-existing clock/seed/suite tests stay green (recedable-clock change is backward-compatible).
- GUI-verified manually (smoke test optional, per 50.6).

---

## 10. Notes / seams carried from 50.6

- `ChatPanel.set_dialogue_mode(bool)` swaps builder ↔ SAY box and **adds/removes** the free-text
  widgets from the `UIManager` (else hidden widgets eat clicks — see auto-memory `feedback_arcade_gui`).
- `_on_chat_send` routes to dialogue while the session is active (currently `_dialogue_stub_active`).
- `disposition` (`Literal["hostile","wary","neutral","willing"]`) + `is_speakable` gate the NPC kind;
  the dungeon kind is gated by resonance + intimacy instead.
- Provider is OpenAI `gpt-4o` via injected `LLMProvider`; `DungeonMasterAgent` is the narration agent
  (`respond(...)` for chat, `request_proposal(...)` for world reactions) — the dungeon channel is a
  sibling agent/mode, not a change to those.
