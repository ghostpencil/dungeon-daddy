# Phase 50.6 — Chat Action Cockpit

**Status:** SPEC (not yet started)
**Type:** BUILD add-on (dynamic, like Phase 50.5 — *not* on the 51–53 roadmap, no GitHub issue).
**Depends on:** Phase 50 (Hybrid Action Model), Phase 50.5 (Use-on grammar).
**Seam toward:** Phase 51 (Talk to the Dungeon) — this phase carves the SAY/ASK input slot
that Phase 51 fills.

---

## 1. Problem

The action loop is physically broken across the screen, and the map overlay is debug-grade:

- The **Action Builder** (`VnaActionPanel`) is buried in the *right* RPG side panel under an
  "ACTION" tab — far from the chat column where the player reads narration and forms intent.
- The **map room overlay** (`_draw_detail_panel`) shows authoring metadata
  (`R1 · role · critical path: No · visual priority`) that no *player* needs mid-scene.
- The two are disconnected: nothing links "the thing I see in the room" to "the noun I act on".

## 2. Goal — close the loop in one column of attention

> **See** the room (map "Things Here" overlay) → **click a thing** → it **pre-fills the action
> sentence** (left chat column) → pick a verb → **ROLL / DO**.

Make the **left chat column the player's cockpit** and turn the map overlay into a **play
surface**, not a debug readout.

```
   MAP (center)                         CHAT COLUMN (left, 440px)
 ┌──────────────────┐                 ┌────────────────────────────┐
 │  THINGS HERE      │   click noun    │  ...narration messages...  │
 │  ► Wall Symbols ──┼───────────────► │  Actor mini-card           │
 │    Scorpion Nest  │   fills noun    │  ┌ ACTION BUILDER ───────┐ │
 │    Scorpions      │   + suggests    │  │ Talvas will [verb] the │ │
 └──────────────────┘   verbs         │  │ [noun] [adverb] [ROLL] │ │
                                       │  └────────────────────────┘ │
                                       └────────────────────────────┘
```

## 3. Decisions locked (design review, 2026-06-24)

| # | Decision | Choice |
|---|---|---|
| 1 | Builder fits the 440px column by… | **Wrapping the sentence to rows** (keep current column width; do not steal map width) |
| 2 | Free-text chat input role | **Contextual SAY/ASK channel** — appears only during "Speak to the Dungeon" events and when dialogue with a *willing* NPC/monster has been initiated. **Not** always visible. The default bottom-of-column input is the Action Builder. |
| 3 | Preview box intelligence | **Deterministic only** — engine-derived, no LLM call on interaction |
| 4 | "Things Here" overlay behavior | **Auto-track the current room**, and it is the **primary** noun picker (click a noun → fills the builder). The builder's noun dropdown remains as a fallback/keyboard path. |

### Baked-in design defaults (lower-stakes, from the same review)

- **Retire the right-panel ACTION tab.** Single source of truth = the in-chat builder. The full
  **Character Sheet (CHAR tab) stays** on the right; the in-chat card stays the compact mini-card.
- **Adaptive action button:** `ROLL` when the action is contested/uncertain; `DO` (or `MOVE` /
  `LOOK`) when it is deterministic (Phase 50's deterministic-vs-contested split).
- **Cyber-arcane palette only.** The brainstorm mockups read blue; re-skin to existing tokens
  (`VIOLET`/`TEAL`/`EMBER`, `BG_1/2/3`, serif room names, `FONT_MONO` chips). No new palette.
- **Overlay taxonomy:** `EXITS · OBJECTS · CREATURES · ITEMS` (loose pickups get their own section).

---

## 4. Surface 1 — In-chat Action Builder

### 4.1 Placement in the left column

Current order (`chat_panel.py`): Header (38) → Room banner (80) → Messages (flex) →
Actor mini-card (96) → Input area (176).

**New order (default / action mode):**

```
Header (38)
Room banner (80)
Messages (flex — gets the remainder)
Actor mini-card (96)
ACTION BUILDER (~200, replaces the old always-on Ask input)
```

Because the free-text Ask box is now contextual (decision #2), only **one** input surface
occupies the bottom at a time, so vertical budget is preserved. On short windows the builder
is **collapsible** (header row with a ▾/▴ toggle) as a responsive fallback.

### 4.2 Layout — wrapped command sentence (re-skinned to tokens)

```
COMMAND SENTENCE                                  ← draw_kicker(), TEAL accent bar
┌──────────────────────────────────────────────┐  BG_2 panel, RADIUS_LG, LINE border
│ Talvas will  [ STUDY ▾ ]  the                 │  "Talvas will" = INK_2; "the" = INK_3
│ [ Wall Symbols ▾ ]      [ carefully ▾ ]       │  verb dd VIOLET-tinted, noun dd TEAL-tinted
│                                  [  ROLL  ]    │  adverb dd dim; ROLL = TEAL flat button
└──────────────────────────────────────────────┘
Suggested:  LOOK   STUDY   SENSE   TINKER  ·move·   ← chips; selected = filled; n/a = INK_4
┌ PREVIEW ─────────────────────────────────────┐  BG_1 inset
│ Likely roll: STUDY                            │
│ Risk: scorpions may stir                      │  EMBER text when a threat is present
│ Memory: discoveries, failures, consequences   │  GOLD/INK_3
└──────────────────────────────────────────────┘
```

**Transitive (Use / Give) variant** — the sentence grows a Target slot (Phase 50.5 grammar
`Verb · Noun · [Target] · Adverb`):

```
│ Talvas will  [ USE ▾ ]  the                   │
│ [ Iron Key ▾ ]  on the  [ Warden Door ▾ ]     │  "on the" = INK_3 connector
│ [ firmly ▾ ]                     [  DO  ]      │
```

The Target slot's presence is driven by `is_transitive(verb)` (already implemented). The
connector word changes per verb family: `on the` for `use`, `to` for `give`.

### 4.3 Slot behavior (reuse existing logic core — no rewrite)

All slot logic already exists in `VnaActionPanel` and `rpg/action_options.py` and is reused
verbatim:

- Verb list: `available_verbs(actor_abilities)`
- Noun list filtered by verb: `available_nouns(...)` + `noun_sources_for_verb(verb)`
- Target list: `target_sources_for_verb(verb)` (transitive verbs only)
- Adverb pool recomputed per chosen noun's `target_type`: `available_adverbs(...)`
- Build + validate: `build_card()` → `validate_card(card, options)` → `submit()`

The **only** changes to the panel object are presentational (the Arcade widget build) plus two
new pure helpers (§4.6). The pure-logic core stays Arcade-free and unit-testable.

### 4.4 Suggested-verbs row

> **RETIRED (2026-06-24, design decision).** Implemented in Slice 5 + polished in CP-4, then
> removed in **CP-6**: the quick-pick row cluttered the builder band. The intent — surfacing the
> most relevant verbs first — is instead served by **ordering the verb dropdown** (alter its sort
> so applicable verbs lead). `verbs_for_noun` stays in `rpg/action_options.py` for that sort and
> for the overlay footer (§5.3). The text below is kept for history.

Quick-select chips below the sentence, **filtered by the selected noun**. Clicking a chip sets
the Verb slot (same effect as the verb dropdown). Verbs that cannot apply to the current noun
render disabled (`INK_4`), matching the greyed `·move·` in the mockup.

- Requires a new inverse helper: **`verbs_for_noun(noun, all_verbs) -> list[VerbOption]`**
  (the dual of `noun_sources_for_verb`). Applicable verbs are enabled; the rest are shown
  disabled, capped at ~5 chips by relevance.

### 4.5 Deterministic Preview box (decision #3 — no LLM)

> **CP-7 (2026-06-24):** the "PREVIEW" kicker was dropped — its accent bar poked above the inset
> and the three lines are self-describing. The box now holds just the lines, centred with
> symmetric padding.

A pure function builds the preview from already-loaded state. **Never** calls the LLM.

| Line | Source (deterministic) |
|---|---|
| `Likely roll: <RATING>` | The action rating the chosen verb resolves against (verb→rating map already in `rpg/`). |
| `Risk: <templated>` | Templated from **room threats present** in `room_context`: hostile creatures → "`<creature>` may stir/attack"; disturbed/hazard objects → named hazard. Empty (hidden) when no threat. Rendered in `EMBER`. |
| `Memory: <tags>` | Which memory types this action *could* create, per existing creation-trigger rules (see `MEMORY_SYSTEM_SPEC.md` — confirm exact type names at impl time; mockup shows discoveries / failures / consequences). |

**Deterministic actions** (e.g. move through an `open` exit, `look`): the preview shows
`No roll — automatic` instead of `Likely roll`, and the button reads `DO`/`MOVE`/`LOOK`.

New helper: **`action_preview(card, room_context, ...) -> ActionPreview`** returning
`(likely_roll: str | None, requires_roll: bool, risk: str | None, memory_tags: list[str])`.
Pure, unit-testable.

### 4.6 Adaptive action button

The submit button label and styling derive from `requires_roll` in the preview:
`ROLL` (contested, TEAL emphasis) vs `DO`/`MOVE`/`LOOK` (deterministic, calmer). On click it
calls the existing `submit()` path (validate → dispatch).

---

## 5. Surface 2 — "Things Here" room overlay

Replaces the technical `_draw_detail_panel` content. **Auto-tracks the current room** (updates on
`MoveParty`); it is the **primary** noun picker (decision #4).

### 5.1 Layout (re-skinned)

```
┌──────────────────────────────────────────────┐
│ THINGS HERE                              [R1] │  kicker + room-id chip (TEAL)
│ Discovered nouns in the current room.         │  INK_3 caption
│ ┌──────────────────────────────────────────┐ │
│ │ Receiving Hall                            │ │  serif (FONT_SERIF), INK_1
│ │ A large room; scorpions present.          │ │  room note, INK_3
│ └──────────────────────────────────────────┘ │
│ EXITS                                          │  section kicker
│  → Marketplace Arch          [ open ]         │  selected = TEAL ring; status chip
│  ↓ Elevator Shaft Door       [ locked ]       │  EMBER chip when locked/blocked
│ OBJECTS                                        │
│  ✦ Wall Symbols              [ unexamined ]   │
│  ⚠ Scorpion Nest             [ disturbed ]    │  EMBER chip
│ CREATURES                                      │
│  ● Scorpions                 [ hostile ]      │  EMBER chip
│ ITEMS                                          │
│  ◆ Brass Fuse               [ on floor ]      │  GOLD accent (loot)
│ ┌ Selected: Marketplace Arch ───────────────┐ │  footer
│ │ Suggested: MOVE, LOOK, SENSE              │ │
│ │ Clicking a noun feeds the action builder. │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### 5.2 Sections & data

Built from `available_nouns(room_context, actor)`, grouped by `NounOption.source`:

| Section | `source` | Status chip from |
|---|---|---|
| EXITS | exit | exit state (`open`/`locked`/`blocked`/`sealed`) |
| OBJECTS | object | object archetype state (`unexamined`/`disturbed`/`ready`/…) |
| CREATURES | creature/npc | disposition (`hostile`/`wary`/`willing`) |
| ITEMS | item | location (`on floor`) / carried |

New view-model helper: **`room_things(room_context, actor) -> RoomThings`** (ordered sections,
each item `(noun_id, label, glyph, status, status_color)`). Pure, unit-testable. Glyphs/status
colors map to existing tokens.

### 5.3 Interaction — the link to the builder

- **Click a noun** → calls the builder's `select_noun(noun_id)` → noun slot fills, adverb pool
  recomputes, suggested-verbs row updates. The clicked row shows a TEAL selection ring.
- The footer mirrors **suggested verbs** for the selected noun (`verbs_for_noun`) and states the
  contract ("Clicking a noun feeds the action builder").
- This makes the overlay the primary picker; the dropdown is the fallback (decision #4).

### 5.4 Positioning

Keep the smart placement logic (`compute_panel_position`) but, since the overlay now auto-tracks
the **current** room rather than an arbitrary selected room, anchor it near the party's room
marker. Width stays ~300px; height grows with section count.

---

## 6. The SAY / ASK channel (contextual — Phase 51 seam)

Decision #2: the free-text input is **not** always present. This phase establishes the
**affordance and the swap**, not the dialogue logic (that is Phase 51):

- The bottom input surface defaults to the **Action Builder**.
- It swaps to a free-text **SAY/ASK** box only when:
  1. a **"Speak to the Dungeon"** event invites direct input, or
  2. the player initiates dialogue with a **willing** NPC/monster (e.g. a `talk`/`sway`-family
     verb on a speakable target whose disposition permits it — not all creatures will talk).
- When dialogue ends, the input swaps back to the builder.

**Phase 50.6 scope:** the swap mechanism + a stubbed/no-op SAY box that can be shown/hidden, and
the "is this target speakable?" gate surfaced in the builder (e.g. the `talk` verb only enabled
on willing targets). **Phase 51 scope:** the actual conversation flow, NPC memory, and routing.
Mark the SAY handler as a Phase 51 extension point.

---

## 7. What changes / what is retired

| Area | Change |
|---|---|
| `chat_panel.py` | New Action Builder region below the actor mini-card; becomes default bottom input. Collapsible on short windows. |
| `vna_action_panel.py` | Logic core reused as-is. Widget layer (`setup_widget`/`draw`) rebuilt for the wrapped chat layout + suggested-verbs row + preview. |
| `rpg/action_options.py` | **New pure helpers:** `verbs_for_noun`, `action_preview`, `room_things` (+ small dataclasses). |
| `_RpgSidePanel` (play_view) | **Retire the ACTION tab.** Re-wire submit callback to the in-chat builder. CHAR/Scene/Fallout/Memory/Debug tabs stay. (Exits tab is now redundant with the overlay — optional retire, follow-up.) |
| `map/.../room_detail_panel.py` + `detail_panel_renderer.py` + `layout_renderer.py` | Replace technical detail content with the "Things Here" view-model + renderer; auto-track current room; noun click callback into the builder. |
| `play_view.py` | Wire overlay-noun-click → builder `select_noun`; keep `_refresh_vna_panel` feeding the relocated builder. |

Preserve-and-extend: no save-format or schema changes expected (UI + pure-logic only). If any
arise, add a migration rather than mutating existing data.

---

## 8. Visual spec (tokens)

- Panels: `BG_2` (builder), `BG_1` (preview inset, overlay), `LINE`/`LINE_HI` borders,
  `RADIUS_LG`.
- Verb slot tinted `VIOLET`; noun slot `TEAL`; adverb `INK_2`; connectors (`the`/`on the`/`to`)
  `INK_3`. Disabled chips/slots `INK_4`.
- Status chips via `draw_chip(...)`: `teal` (open/ready/willing), `ember` (locked/disturbed/
  hostile/blocked), `gold` (loot/items), `default` (neutral).
- Room name in overlay: `FONT_SERIF`; section kickers via `draw_kicker`; chips/preview in
  `FONT_MONO`.
- Action button: `ROLL` TEAL emphasis; `DO`/`MOVE`/`LOOK` calmer (`BG_3`/`LINE`).

---

## 9. Slice plan (TDD — read `spec/TESTING.md` and use the TDD skill before each)

Logic-first, then widgets via the ui-test harness. Each slice is one behavior.

1. **`verbs_for_noun`** — pure helper + unit tests (applicable vs disabled verbs per noun source).
2. **`action_preview`** — pure helper: likely-roll/requires_roll, templated risk from room
   threats, memory tags; deterministic-action case.
3. **`room_things`** — view-model grouping `available_nouns` into Exits/Objects/Creatures/Items
   with status chips; ordering + empty-section handling.
4. **Builder widget relocation** — render the wrapped sentence + slots in `chat_panel`; verify
   slot population/selection via ui-test harness; submit dispatches a valid card.
5. **Suggested-verbs row** — chips set the verb; inapplicable verbs disabled.
6. **Preview box render** — wires `action_preview`; adaptive button label (ROLL vs DO).
7. **"Things Here" overlay** — replace detail content; auto-track current room; render sections.
8. **Overlay→builder link** — clicking a noun fills the builder noun slot + refreshes suggestions.
9. **Retire ACTION tab** — remove tab, re-wire submit to in-chat builder; suite stays green.
10. **SAY/ASK swap (stub)** — input surface swaps builder↔SAY box on a dialogue flag; `talk`
    verb gated to willing targets. (Conversation logic deferred to Phase 51.)
11. **Polish + smoke test** — `tools/smoke_test_phase*.py` (Strategy A/B per TESTING.md); manual
    visual verify by the user. **Includes dynamic builder-band height** (see below) and the
    short-window collapsible fallback (§4.1).

> **Slice 11 requirement — dynamic band height.** `_BUILDER_H` is currently a fixed **180px**
> (chosen 2026-06-25 after CP-6 freed the suggested-row space). At 180 the top-anchored command
> sentence has room for ~3 wrapped lines before its lowest chip collides with the bottom-anchored
> preview inset — which covers the realistic worst case (transitive `V·N·T·A` with long labels).
> The cost is an airy gap when the sentence is short. Slice 11 should make the band **size to the
> actual sentence line count** so the sentence↔preview gap stays constant: the builder must
> *measure* its wrapped sentence height (the CP-1 `_wrap_units` line assignment already yields the
> line count) and expose it so `chat_panel`'s layout (`_builder_extra_h`/`_BUILDER_H`) consults it
> instead of a constant. This removes both the empty-gap-when-short and collision-when-long cases.

## 10. Non-goals

- No actual conversation/dialogue logic (Phase 51).
- No new RPG mechanics, schema, or save-format changes.
- No new libraries; Arcade-native widgets only.
- No LLM call in the preview or the builder (advisory-only boundary holds).
- No palette/visual-language change beyond applying existing tokens.

## 11. Open questions / to confirm at implementation time

- Exact memory **type names** for the preview's "Memory" line (verify against
  `MEMORY_SYSTEM_SPEC.md`).
- Whether the redundant **Exits tab** on the right panel is retired now or left as follow-up.
- Glyph set for overlay rows (→ ↓ ✦ ⚠ ● ◆) — confirm font glyph coverage or use icon PNGs
  (`assets/ui/icons/`, `game-icon-finder` skill) if `FONT_MONO` lacks them.
- Minimum window height threshold at which the builder auto-collapses.
```
