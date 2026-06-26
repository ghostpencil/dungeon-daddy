# Dungeon Daddy — Project Index

## Phase

Phase **50 — Hybrid Action Model: COMPLETE & merged to `main`** (2026-06-23).
Phase **50.5 — Use Noun on Noun: COMPLETE & merged to `main`** (PR #81, 2026-06-24).
Phase **50.6 — Chat Action Cockpit: COMPLETE, GUI-verified & merged to `main`** (PR #82, 2026-06-26).
All 11 slices done/user-verified (+ CP-1…CP-7 polish; Slice 8 three UX rounds; Slice 9 retired ACTION
tab; EXITS/Move tab also retired); Slice 11 (dynamic band height + reclaim + collapsible toggle +
bottom-click UIManager fix) DONE & GUI-verified — smoke test skipped by user choice.
Phase **51 — Talk to the Dungeon: IN PROGRESS** on branch `phase-51` (started 2026-06-26).
Decisions locked; **Slices 1–3 DONE & committed**; Slice 4 (intimacy gate) next.

Specs: current/future phases in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (index:
`spec/IMPLEMENTATION_PHASES.md`). Phase 50.5 spec: `spec/PHASE_50_5_USE_ON_GRAMMAR.md`.
Phase 50.6 spec: `spec/PHASE_50_6_CHAT_ACTION_COCKPIT.md`.
Phase 51 spec: `spec/PHASE_51_TALK_TO_THE_DUNGEON.md`.

---

## START HERE next session — Phase 51 in progress; Slice 4 next

**Phase 51 — Talk to the Dungeon** is underway on branch `phase-51` (off `main`). The spec is
**finalized** (`spec/PHASE_51_TALK_TO_THE_DUNGEON.md`, commit `7a36905`); decisions are locked (§3).

**Slices 1–3 — DONE & committed.** S1 (`d4770a7`): three optional `CampaignManifest` fields. S2
(recedable clock engine): `ClockState.monotonic: bool = True` (`rpg/models.py`) + signed
`tick_clock(clock, delta) -> ClockState` (`rpg/clocks.py`, clamps `[0, segments]`; latches
`completed` at full only when monotonic; non-monotonic recedes and never latches) +
`advance_clock` unchanged (regression-guarded) + migration `016_clock_monotonic.sql`
(`clocks.monotonic BOOLEAN DEFAULT true`). +7 tests (2 model, 5 engine). S3 (resonance archetype):
`"resonance_point"` added to the `ObjectArchetype` Literal (`rpg/models.py`); `build_room_context`
(`rpg/room_context.py`) now **derives** `resonance_point` — `True` when the room contains a
`resonance_point` object (OR'd with the explicit param, which stays for callers). +3 tests (1 model,
2 context). rpg+memory suites green (787). **Note:** repo `save_clock`/`get_clocks` do NOT yet
persist `monotonic` (named SELECT, so the new column is harmless/default-true on read) — wire it in
the seed slice when the intimacy clock needs `monotonic=False` persisted. The **manifest** object
`archetype` Literal (`campaign/manifest.py:95`) was deliberately **left without** `resonance_point`
(no seeding in this pure slice) — add it in the seed slice when authoring resonance rooms.

**Slice 4 next — intimacy gate (spec §4.3 / §7.4).** Pure helper
`dungeon_channel_available(room_context, intimacy_clock) -> (bool, reason)`: open only when the room
is a **resonance point** (`room_context["resonance_point"]`) **AND** the intimacy clock is at/above
threshold; returns the lock reason string when closed (not-here vs. not-intimate-enough). Reads
`filled`/`segments` **live** (non-monotonic clock; never a completion event). Pure helper slice (no
lib, no LLM, no UI). Use the TDD skill (read `spec/TESTING.md` first); check spec §4.3 for the band
thresholds.

Scope: a freeform **dungeon-voice** channel gated by **resonance points** (seed-marked rooms) + a
**recedable dungeon-intimacy clock** (`monotonic=False`). The LLM plays the dungeon's voice (advisory
only); the **engine** ticks intimacy + drafts memory. The 50.6 NPC `sway→willing` stub folds into the
same shared dialogue engine (decision D1).

**Slice plan (TDD, spec §7):** 1 manifest fields → 2 **recedable clock engine** (`monotonic` +
signed `tick_clock`; the risky backward-compat slice — keep all clock/seed tests green) → 3 resonance
archetype → 4 intimacy gate → 5 knowledge filter → 6 dungeon-voice bundle+agent → 7 engine
side-effects (tick + draft memory) → 8 PlayView routing (fold in NPC kind) → 9 UI treatment →
10 (optional) corruption scaffold. Use the TDD skill (read `spec/TESTING.md` first).

**Locked decisions (spec §3):** D1 shared engine (dungeon full + NPC folded in) · D2 `resonance_point`
archetype + overlay affordance · D3 seed-authored intimacy clock · D4 engine-drafted memory ·
D5 corruption scaffold only · D6 no LLM proposals.

**Branch note:** an earlier docs-only index sync (50.6-merged wording) is on `docs/index-50.6-merged`
(commit `699495d`), not yet merged to `main`; this index now carries that correction directly.

---

## Phase 50.6 — COMPLETE & merged (history)

**Slice 11 (final) — DONE & GUI-verified, smoke test skipped by user** (manual verify sufficient;
cockpit likely to evolve). Four pieces:
1. **Dynamic band height** — `_BUILDER_H` (fixed 180) **removed**; band sizes to the wrapped sentence
   via `InChatActionBuilder.sentence_line_count(w)`/`content_height(w)` (share `_sentence_units()` with
   `draw()`); `chat_panel._builder_extra_h` + builder draw consult `content_height(self._w)`, keeping a
   constant `_SENTENCE_PREVIEW_GAP`.
2. **Blank-strip reclaim** — mini-card stacks directly on the band via `_card_bot_off` +
   `_BUILDER_BOTTOM_PAD`; `_input_area_h` no longer reserves the hidden input row.
3. **Collapsible ▾/▴ toggle** — full-width **ACTION … ▾ show / ▴ hide** bar; `is_collapsed()`/
   `toggle_collapsed()`/`apply_auto_collapse(bool)` (manual latches `_user_toggled`); `chat_panel.
   _apply_builder_auto_collapse()` auto-collapses when panel height < `_BUILDER_AUTOCOLLAPSE_H = 620`.
4. **Bottom-click UIManager fix** (the big one) — the reclaim pushed the builder's button/toggle into
   the bottom ~62px where the **hidden free-text `UIInputText`/`UIFlatButton`, though `visible=False`,
   were still registered with the UIManager and intercepted every click there** (dead action button +
   "can collapse but not reopen"). Fix: `_apply_input_visibility` **adds/removes the free-text widgets
   from the UIManager** with visibility (removed in builder mode, re-added on dialogue); `chat_panel`
   tracks `_manager` + `_free_text_in_manager`. See auto-memory [[feedback_arcade_gui]].

**Possible follow-up to weigh (user, 2026-06-25):** now that clicking an open exit auto-moves,
consider dropping the `move` verb from the in-chat command sentence — TBD, revisit once played.

Spec is `spec/PHASE_50_6_CHAT_ACTION_COCKPIT.md` (design decisions locked in §3). Phase 50.6 is a
**BUILD add-on** (dynamic, like 50.5 — not on the 51–53 roadmap, no issue).
Goal: close the action loop in the left chat column — move the Action Builder out of the right
RPG panel into the chat, and turn the map room overlay into a clickable "Things Here" noun picker.

Mostly a relocation + re-skin: `VnaActionPanel`'s pure-logic core is reused verbatim; only the
Arcade widget layer is rebuilt, plus 3 new pure helpers. 11-slice TDD plan in spec §9.

**Phase 50.6 was on branch `phase-50.6`, now merged to `main`** (PR #82). Use the TDD skill
(read `spec/TESTING.md` first).

**Slot-widget decision (locked, 2026-06-24):** the in-chat builder's V/N/T/A slots are
**custom-drawn chips that open a popup list on click** — NOT a cycle picker, NOT native
`arcade.gui.UIDropdown` (re-affirms Phase 50 feedback; see auto-memory
`project_phase50_vna_dropdowns`). The right-panel ACTION tab was kept alongside the new
in-chat builder until **Slice 9 retired it** (in-chat builder is now the sole action surface).

- **Slice 1 — DONE** (commit `e6b6a6e`): `verbs_for_noun` pure helper (inverse of
  `noun_sources_for_verb`) in `rpg/action_options.py` + 4 unit tests. Full rpg unit suite green.
- **Slice 2 — DONE** (commit `ef1193b`): `action_preview` pure helper + `ActionPreview`
  dataclass (spec §4.5) in `rpg/action_options.py` + 10 unit tests. `likely_roll`/`requires_roll`
  (skill/class verbs + use-on-creature roll; move/pick-up/equip/activate/give/combine/look +
  use-on-self deterministic), templated `risk` from live room threats, `memory_tags`. **§11
  resolved:** Memory line uses **canonical** `MEMORY_SYSTEM_SPEC` type names (event/fallout/
  location/dungeon_state/relationship), not the mockup's flavor words. Full rpg unit suite green.
- **Slice 3 — DONE** (commit `eb4a475`): `room_things` view-model + `RoomThings`/
  `ThingsSection`/`RoomThing` dataclasses (spec §5.2) in `rpg/action_options.py` + 13 unit
  tests. Groups `available_nouns` into ordered EXITS/OBJECTS/CREATURES/ITEMS; rows carry
  `(noun_id, label, glyph, status, status_color)`. status_color → existing `draw_chip` tokens
  (teal/ember/gold/default); objects get hazard glyph `⚠` when disturbed/armed; creatures
  prefer `disposition` over actor `status`; key-gated open exits read "locked"; items gold;
  synthetic self/room (+ ally party) dropped; empty sections omitted. Full rpg unit suite green.
- **Slice 4 — DONE** (commit `43456f2`; first widget slice): Builder widget relocation (spec §4.1–4.3).
  New `dungeon_daddy/ui/panels/action_builder.py` → `InChatActionBuilder`, which **reuses
  `VnaActionPanel`'s Arcade-free logic core verbatim** (`*_labels()`/`select_*_by_label()`/
  `submit()`) and adds only a presentational layer: wrapped command sentence ("`<Actor>` will
  [VERB] the [NOUN] [ADVERB]"; transitive verbs grow a Target slot with connector "on the"/"to"),
  **custom-drawn slot chips that open a popup list on click** (popup-row click selects + closes;
  outside-click dismisses; action button calls `submit()`). 10 unit tests
  (`tests/unit/ui/panels/test_action_builder.py`): slots order, transitive target slot, popup
  open/select/dismiss, button-submits-valid-card, and a `draw()`-records-hit-rects test (mocks
  the draw primitives → guards draw/hit-test agreement headlessly). Wired in:
  `chat_panel.py` draws the builder band below the actor mini-card in play mode (band adds
  ~156px; `_builder_extra_h`/`set_action_builder`; routes `on_mouse_press`; popup drawn **last**
  so it overlays the card/messages), and `play_view.py` builds `InChatActionBuilder(self._rpg_vna)`
  so `_refresh_vna_panel()` feeds it and `submit()` routes through `_on_vna_submit`. ACTION tab
  kept alongside. Full UI+views unit suite green (935). **Caveats:** `ROLL` button label is a
  placeholder (Slice 6 makes it adaptive ROLL/DO/MOVE/LOOK via `action_preview`); band height not
  yet responsive/collapsible (Slice 11). **Not done:** ui-test-harness visual check — user
  verifies the GUI manually (`python -m dungeon_daddy` → Play mode, room loaded).
- **Slice 5 — DONE** (commit `96f2db0`): Suggested-verbs row (spec §4.4) in
  `InChatActionBuilder`. `suggested_verbs() -> list[(label, enabled)]` ranks verbs **applicable
  to the selected noun** (`verbs_for_noun`) first/enabled, the rest tagged disabled; `draw()`
  applies the ~5 cap (VIOLET chips; greyed `INK_4` when disabled) and records `_suggested_rects`;
  `on_mouse_press` routes an **enabled** chip → `select_verb_by_label` (a disabled chip consumes
  the click but is a no-op). Two new presentational read-accessors on `VnaActionPanel`
  (`verb_options()`, `selected_noun_option()`). 5 new unit tests (chip tagging, applicable-ranked-
  first, enabled-click-sets-verb, disabled-click-noop, draw-records-capped-rects). **Design note:**
  the pool always has 8+ always-applicable universal verbs, so `suggested_verbs()` returns the
  **full** ranked list (disabled tags stay testable) and the cap lives in `draw()` — in the live
  app the drawn ~5 are normally all enabled. Full UI+views+rpg unit suite green (1525).
- **Slice 6 — DONE** (preview render + adaptive button, spec §4.5–4.6). `VnaActionPanel` now
  retains the raw `room_context`/`actor` mappings (set in `set_context`) and exposes
  `preview() -> ActionPreview | None` (builds the Card, delegates to the pure `action_preview`
  helper from Slice 2). `InChatActionBuilder` gains `preview_lines()` (Likely roll / "No roll —
  automatic"; a `Risk:` line only when a live room threat is present, drawn EMBER; a `Memory:`
  line of canonical tags) and an **adaptive `button_label()`** — `ROLL` when contested/no-card,
  else `MOVE`/`LOOK` for those verbs / `DO`. `draw()` renders a BG_1 PREVIEW inset above an
  adaptive button (TEAL emphasis for ROLL; calmer BG_3/LINE/INK_2 for DO/MOVE/LOOK). 8 new unit
  tests (button label per verb-class + 4 preview-line cases incl. empty-without-card).
- **Slice 6 manual-verify fixes — DONE** (commits `7c47b60`, `ba739e2`; user verified the GUI):
  1. **Builder empty on load** → `set_rpg_context` now calls `_refresh_vna_panel()` as its last
     step (it runs after `load_dungeon_session`, whose `_focus_party_room` fires while `_mem_repo`
     is still `None`, so it is the first point room+actors+repo are all ready). Previously the
     builder showed `— will [—] the [—]` until the right-panel ACTION tab was opened.
  2. **Actor switch didn't update the sentence** → `_on_actor_switch` (the chat mini-card `< >`
     picker) now also calls `_refresh_vna_panel()`, mirroring the CHAR-tab `_set_acting_actor`
     path (skipped while awaiting confirmation).
  3. **"Look the …" grammar** → builder gained a verb-specific `_noun_connector()`; LOOK reads
     "<Actor> will Look **at the** <noun>" (default stays "the").
  4. **"COMMAND SENTENCE" kicker removed** (read too technical, cost a row); sentence now starts
     at the top. Band height `_BUILDER_H` settled at **180** (was bumped 150→200 in Slice 6, then
     trimmed). A decorative frame to highlight the builder region is a later polish.
  4 new unit tests. Full UI+views unit suite green (952).
- **Command-Sentence Polish (CP-1…CP-5) — DONE** (commits `3a5851f`, `5a0e82d`, `4dd12ad`; user
  verified the GUI). A design-review pass on the in-chat builder's command sentence (Surface 1
  refinement; pulls Slice 11 polish forward, respects locked spec §8 color scheme — keeps per-slot
  tints rather than removing color coding). All in `InChatActionBuilder` draw layer + pure helpers:
  1. **CP-1 clause-aware wrap** — pure `_wrap_units` (keep-with-previous grouping) glues a
     noun/target connector to its slot so a wrap never orphans "the"/"on the"/"to"; `draw()`
     rewired from per-token wrap to a two-pass unit layout. 3 unit tests.
  2. **CP-2 adverb contrast** — adverb slot tint `INK_3`→`INK_2` (spec §8 alignment; was shipped
     dim). All slots share identical chrome (BG_3 fill, 1px border, ▾ caret) so the tint is the
     only role differentiator and the adverb reads as editable, not static. Visual.
  3. **CP-3 empty-slot placeholder** — an unset slot draws its dim `INK_4` role word
     ("verb"/"noun"/"target"/"how") instead of "—". New `slot_is_unset(kind)` predicate + 2 tests.
  4. **CP-4 suggested active-fill** — the suggested chip matching the current verb draws filled
     (vs outlined), distinguishing the quick-pick row from the verb slot (spec §8 "selected =
     filled"). New `_suggested_is_active(label)` + 1 test.
  5. **CP-5 connector calm** — actor name kept `INK_2` (content), "will" dropped to `INK_3` to
     match the other glue words; all function words now one quiet weight. Visual.
  6 new unit tests total. Full UI+views unit suite green (958).
- **Builder declutter (CP-6, CP-7) — DONE** (user-requested; user verified the GUI). Two removals
  on the builder band:
  1. **CP-6 drop suggested-verbs row** — **retires spec §4.4 / Slice 5** (it cluttered the band).
     Removed the draw block, click routing, `_suggested_rects`, and
     `suggested_verbs`/`_suggested_is_active`/`_SUGGESTED_CAP` (+6 tests). The "relevant verbs
     first" intent moves to **ordering the verb dropdown** later if needed; `verbs_for_noun` stays
     in `rpg/action_options.py` for that sort + the overlay footer (§5.3).
  2. **CP-7 remove PREVIEW kicker** — the `draw_kicker` accent bar poked above the inset; dropped
     it and re-padded so the preview lines sit centred with symmetric top/bottom padding.
  Net −5 tests. Full UI+views unit suite green (953).
  **Band height (decided 2026-06-25):** keep `_BUILDER_H` fixed at **180** — the freed suggested-
  row space is intentional headroom for the top-anchored command sentence (~3 wrapped lines clear
  the preview, covering transitive `V·N·T·A`). **Dynamic band height** (size to actual sentence
  line count, kill the airy-when-short gap) is now a **Slice 11 requirement** (spec §9).
- **Slice 7 — DONE** (overlay content swap, spec §5; user verified the GUI). The play-mode map
  room overlay now renders the player-facing **"Things Here"** view-model instead of the graph
  authoring readout (`GRAPH MODE / Critical Path / Visual Priority`). **Content only — placement
  untouched:** the overlay already auto-tracks the current room (play mode feeds the party room
  into `set_selected_room`) and `compute_panel_position` already anchors to it, so `panel_placement`
  was NOT changed (user constraint). New pure `format_things_here(RoomThings) -> list[PanelLine]`
  in `detail_panel_renderer.py` (+ `PanelLine` gains optional `status`/`status_color` for chip
  rows); `layout_renderer.draw()` gains `mode`/`room_things` params — `mode=="play"` renders the
  Things-Here lines and draws EXITS/OBJECTS/CREATURES/ITEMS status chips via `draw_chip`
  (teal/ember/gold), with per-line height so chips don't collide; **graph/design mode is the
  default and unchanged** (regression-guarded). Wiring: `MapPanel.set_things_here()` forwards
  `mode="play"`+`room_things` (gated to the current level); `play_view._refresh_vna_panel` builds
  `room_things` from the same room_context/actor it already feeds the builder, so the overlay
  updates on load **and every move**. **Decision (user, 2026-06-25):** carried **party inventory
  is dropped from the overlay** (`SOURCE_CARRIED_ITEM` removed from `_SOURCE_SECTION`) — it is on
  the party, not in the room; the builder noun dropdown still surfaces it via `available_nouns`;
  inventory gets its own surface later. **Renderer-injection decision (locked):** mode flag in the
  renderer (not a pre-built-lines override); play_view builds the `RoomThings` view-model so the
  map layer takes no RPG imports beyond the dataclass type. 9 new tests (3 helper, 3 renderer incl.
  graph-mode regression, 2 MapPanel draw-forwarding, 1 play_view feeds-overlay; + carried-exclusion
  test inverted). Full unit suite green (2916).
- **Slice 8 — DONE** (overlay→builder link, spec §5.3; **user-verified** after 3 UX rounds below).
  Clicking a "Things Here" row now fills the in-chat builder's noun slot, rings the clicked row TEAL,
  and mirrors that noun's suggested verbs in the overlay footer. (NOTE: the ring + footer described
  here were superseded by the UX rounds — see below for the shipped marker/no-footer design.) Four
  TDD cycles: (1) **view-model** —
  `detail_panel_renderer.PanelLine` gains `noun_id` + `selected`; `format_things_here(things,
  selected_noun_id, suggested_verbs)` flags the selected row and appends a footer (`Selected: <label>`
  / `Suggested: <verbs>` / "Clicking a noun feeds the action builder."); footer only when a noun is
  selected. (2) **renderer** — `LayoutRenderer.draw` forwards `selected_noun_id`/`suggested_verbs` to
  `format_things_here`; `_draw_detail_panel` records per-row **screen rects** keyed by `noun_id`
  (exposed via `thing_rects()`, reset each draw) and draws a TEAL ring (`_SELECTION_WIDTH`) on the
  selected row. (3) **MapPanel** — new `on_noun_click` ctor callback; `set_things_here` gains
  `selected_noun_id`/`suggested_verbs` (passed through to the renderer, gated to the current level);
  `handle_mouse_press` hit-tests `thing_rects()` **first** in play mode so overlay rows take priority
  over the room/edge select underneath. (4) **play_view** — `_on_overlay_noun_click(noun_id)` calls
  `self._rpg_vna.select_noun` then a new lighter `_push_things_here_overlay()` (rebuilds `RoomThings`
  from the **retained** `_last_room_context`/`_last_actor_dict` + reads the panel's selection +
  `verbs_for_noun` capped at `_OVERLAY_SUGGESTED_CAP=4`) — deliberately **not** a full
  `_refresh_vna_panel`, because `set_context` resets the noun to default. `_refresh_vna_panel` now
  retains that context and routes its overlay feed through the same helper; `on_noun_click` is wired
  into the `MapPanel(...)` ctor. **Design note:** a real move still does a full refresh → resets to
  the default noun (correct); only a click selects-and-re-pushes without rebuilding. 15 new tests
  (5 view-model, 3 renderer, 4 MapPanel, 3 play_view). Full unit suite green (2931).
- **Slice 8 selection-cue fix — DONE** (user-reported; GUI screenshot). The TEAL **rectangle ring
  was misaligned** (drawn a row low) because `arcade.draw_text` anchors at the **baseline** (text
  draws *above* `y`) while the rect was computed *below* `y` — the hit-rects had the same offset.
  Fix + redesign per user suggestion: (1) **centre the clickable rect on the drawn text**
  (`row_center = y + _THING_ROW_CENTER_DY`; the status chip now shares that center too); (2)
  **replace the rectangle with a per-row marker glyph** — `format_things_here` prepends `_SEL_MARKER`
  "▸" to the selected row and `_UNSEL_MARKER` "·" to the rest (radio-style; glyphs are in the same
  Unicode blocks as the existing ●/◆ row glyphs, so no PNG assets needed), and the renderer tints
  the selected row's text TEAL (`_PANEL_SELECTED_COLOR`). The ring (`draw_rect_outline` in the
  panel) is gone. Net tests: −1 ring test, +3 (marker, rect-centred regression, selected-text-teal).
  Full map+ui+views suites green (1628).
- **Slice 8 UX round 2 — DONE** (user-requested; 3 items). (1) **Larger selection marker** — the
  per-row marker moved out of the row text into `PanelLine.marker`; the renderer draws it in a left
  gutter (`_PANEL_MARKER_COL_W=16`), the selected `▸` at `_PANEL_MARKER_FONT_SIZE=13` + bold + TEAL,
  the deselected `·` quiet (dim, normal size). (2) **Click an open exit = auto-move** —
  `_on_overlay_noun_click` now: if the clicked noun is an **open** exit (`source==SOURCE_EXIT`),
  `select_verb(move)` + `select_noun` + `submit()` (walks through it, no verb pick); a **locked**
  exit (`SOURCE_LOCKED_EXIT`) and every non-exit still take the select-and-feed-builder path. (Test
  helper `_make_view` now wires `set_submit_callback`, matching the real ctor.) **Open follow-up:**
  if auto-move feels right we may drop the `move` verb from the command sentence — TBD. (3) **Loop
  chips gated** — `MapPanel.set_loops_visible(bool)` (loop-pattern pills are an authoring/test-drive
  affordance); `play_view` shows them in `load_dungeon_transient` (test drive) and **hides them in
  `load_dungeon_session`** (real play). 7 new tests (1 view-model marker, 1 renderer marker-size,
  2 play_view auto-move, 3 MapPanel loop-gating; 3 prior overlay tests retargeted to locked exits).
  Full map+ui+views suites green (1634).
- **Slice 8 UX round 3 — DONE** (user-requested; 3 items). (1) **Footer removed** — the
  Selected/Suggested/"Clicking a noun…" footer is gone; `format_things_here` no longer emits
  `"footer"` lines, and the `suggested_verbs` plumbing was removed end-to-end (param dropped from
  `format_things_here`/`LayoutRenderer.draw`/`MapPanel.set_things_here`; `play_view` no longer
  computes `verbs_for_noun` for the overlay or keeps `_OVERLAY_SUGGESTED_CAP`). `verbs_for_noun`
  stays in `rpg/action_options.py` for the later verb-dropdown ordering. (2) **Click a loose item =
  auto-pickup** — `_on_overlay_noun_click` generalised to an `{SOURCE_EXIT: move, SOURCE_LOOSE_ITEM:
  pick-up}` map; clicking a floor item picks it up with the acting actor. (3) **Room code folded into
  the header** — `"R4: THINGS HERE"` instead of a separate `R4` row (saves a vertical line). Net
  tests: −3 footer/suggested (renderer + 2 view-model), +2 view-model (no-footer, header-folds-id),
  +1 play_view loose-item pickup; the "feeds-selected" test trimmed to selection-only. Full
  map+ui+views suites green (1633).
- **Reseed / no-playbook crash fix — DONE** (commit `ca9af45`, 2026-06-25; not a slice — surfaced
  while reseeding the Crucible save to test Slice 8). A `--force` RPG reseed had blanked the PCs'
  `playbook_slug`, and loading the save then crashed in the action panel (`available_adverbs("")` →
  `KeyError`). Two fixes + tests: (1) `vna_action_panel._refresh_adverbs` treats an empty playbook
  slug like `None` (offers no adverbs, no crash); (2) `seed_rpg_state` `--force` now preserves the
  existing actor's `playbook_slug`/`room_id`/`status` (the pack doesn't own them). The live Crucible
  save was repaired by restoring the 3 PCs' playbooks from `campaign.duckdb.bak-prepopulate`
  (kira→fighter, mira→artificer, talvas→thief; `protagonist` is blank by design). Reseed-a-save
  invocation gotchas captured in **Notes** (`--campaigns-dir` for the saves dir; `PYTHONPATH=.` for
  the populate scripts). Full unit suite green (2940).
- **Slice 9 — DONE** (retire ACTION tab, spec §7 + §9.9; suite green 2938, **GUI-verified 2026-06-26**).
  The right-panel **ACTION tab is removed** — the in-chat builder is now the single action surface.
  In `play_view.py`: dropped `"ACTION"` from `_RPG_TAB_LABELS`, removed `_TAB_ACTION`, reindexed
  `_TAB_EXITS`/`_TAB_DBG`; stripped the `action_panel` from `_RpgSidePanel` (ctor param + `setup`/`teardown`/
  `set_active`/`draw` branches + the `refresh_action_widget` method); removed the `_TAB_ACTION`
  branch in `on_mouse_press` and both `side.refresh_action_widget()` calls (the in-chat builder
  reads `_rpg_vna`'s options **live each draw**, so no widget rebuild is needed). `_rpg_vna` + its
  `set_submit_callback(_on_vna_submit)` + the `InChatActionBuilder` wiring are **unchanged** —
  submit already routed through the in-chat builder since Slice 4, so "re-wire submit" was a no-op.
  Tests (`test_play_view_bundle.py`): inverted the tab-registration test
  (`test_action_tab_retired_from_rpg_tab_labels` + `test_remaining_rpg_tabs_kept`), **deleted the
  obsolete `TestRpgSidePanelActionLifecycle` class**, dropped the `action` arg from `_make_rpg_side`.
  **Note:** `tools/smoke_test_phase33.py` still references an ACTION tab but is a stale Phase-33
  manual tool (already out of date — hardcoded a 6-tab layout) and isn't in the suite; left as-is,
  the Phase 50.6 smoke test is Slice 11. The legacy `_rpg_action` (`PlayerActionPanel`, Phase 33
  resolve flow) is untouched — it was never a tab.
- **EXITS / Move tab retired — DONE** (follow-up to Slice 9, user-requested 2026-06-26; spec §7 had
  flagged it redundant with the "Things Here" overlay now that clicking an exit auto-moves). Right
  panel now has **5 tabs (CHAR/SCENE/FALLOUT/MEM/DBG)**. The `ExitListPanel` widget became dead code
  (only the tab used it), so it was **fully deleted** (`dungeon_daddy/ui/panels/exit_list_panel.py`
  + `tests/unit/ui/panels/test_exit_list_panel.py`) along with `_refresh_exits()` and `_exit_panel`.
  In `play_view.py`: dropped `"EXITS"`/`_TAB_EXITS`, reindexed `_TAB_DBG` to 4, removed the
  `exit_panel` from `_RpgSidePanel` (ctor + setup-loop + draw branch), removed the `_TAB_EXITS`
  mouse-press branch, and removed all 4 `_refresh_exits()` call sites (room-click select,
  `_focus_party_room`, exit-unlock, `_on_exit_move`) — the overlay/builder are fed by
  `_refresh_vna_panel`/`_push_things_here_overlay` instead. **Kept:** `_on_exit_move` (the engine
  move command, still driven by overlay click-to-move + builder `move`). Tests: added
  `test_exits_tab_retired_from_rpg_tab_labels`, updated `test_remaining_rpg_tabs_kept` to the 5-tab
  list; `test_play_view_exits.py` trimmed to the `_on_exit_move` cases (dropped the two
  `_refresh_exits` tests); `conftest.py`/`test_play_view_vna.py` dropped the `ExitListPanel`
  scaffolding; `test_play_view_party_focus.py` dropped the `_refresh_exits` mock + assertions.
- **Slice 10 — DONE** (SAY/ASK swap stub + creature `disposition`, spec §6 + §9.10; **committed &
  GUI-verified 2026-06-26**; full unit suite green **2960**). Two halves — the input-surface swap and
  a real `disposition` field so the gate can fire live. **8 TDD cycles:**
  1. **`is_speakable(noun, room_context)`** pure helper in `rpg/action_options.py` + consts
     `VERB_SWAY`/`DIALOGUE_VERBS`/`_SPEAKABLE_DISPOSITIONS={"willing"}`. A creature noun (NPC/monster)
     is speakable only when its `disposition` is `willing`; non-creatures and hostile/wary never are.
     (No `talk` verb exists — `sway` is the talk/sway-family social verb.) +6 tests.
  2. **Builder dialogue gate** — `VnaActionPanel.selected_noun_is_speakable()`; `InChatActionBuilder.
     is_dialogue_action()` (verb in `DIALOGUE_VERBS` **and** selected noun speakable); `button_label()`
     returns **TALK** for a dialogue action. +7 tests.
  3. **`ChatPanel.set_dialogue_mode(bool)`** swap — default play mode shows the builder and **hides**
     the free-text input; dialogue shows the SAY box and hides the builder. `_builder_visible()`/
     `_free_text_visible()` gate `_builder_extra_h`, the builder draw, and click-routing; `setup()`/
     `set_action_builder()` apply visibility. +6 tests.
  4. **play_view wiring** — `_on_vna_submit`: a `sway` on a **speakable** target calls
     `_begin_dialogue_stub(noun)` (sets `_dialogue_stub_active`, `chat.set_dialogue_mode(True)`, posts
     a placeholder) **instead of rolling**; hostile/wary `sway` falls through to the normal roll.
     `_on_chat_send` routes a line to `_on_dialogue_send_stub` while `_dialogue_stub_active` (ends the
     stub, swaps back). **Both stub handlers are marked Phase 51 extension points.** Send-interception
     keyed off the **PlayView flag** (not the mocked chat) — avoids a `MagicMock` truthiness trap that
     first broke 47 pending-intent tests (caught + fixed pre-green). +3 tests.
  5–8. **Real `disposition` data** (user chose "Add disposition field" over a tag fallback —
     authorized override of the §10 "no schema change" non-goal): **migration `015_actor_disposition.
     sql`** (`actors.disposition TEXT DEFAULT 'neutral'`); `ActorState.disposition: Literal["hostile",
     "wary","neutral","willing"]="neutral"`; `save_actor`/`get_actor`/`get_actors_by_room` persist +
     return it; `context_bundle._actor_noun` emits it into npc/monster rows. **Pinion (R3)** seeded
     `disposition="willing"` in `tools/populate_crucible_level1.py`. End-to-end test: real repo →
     `build_room_noun_context` → `available_nouns` → `is_speakable` True. +9 tests (model, repo,
     context incl. 2 exact-equality npc/monster dicts updated to carry `disposition`).
  **Live save updated this session** (user-requested): backed up to `campaign.duckdb.bak-slice10-*`,
  applied migration 015, re-ran `populate_crucible_level1` — Pinion now `willing` (verified speakable).
  **Files:** `rpg/action_options.py`, `ui/panels/action_builder.py`, `ui/panels/vna_action_panel.py`,
  `ui/panels/chat_panel.py`, `views/play_view.py`, `rpg/models.py`, `memory/repository.py`,
  `memory/context_bundle.py`, `data/migrations/015_actor_disposition.sql`, `tools/populate_crucible_level1.py`.
- **Slice 11 — DONE & GUI-verified** (polish; spec §9.11; **smoke test skipped by user choice** —
  manual verify sufficient, cockpit likely to evolve). Four pieces:
  1. **Dynamic band height** — `InChatActionBuilder.sentence_line_count(w)`/`content_height(w)` (built
     on shared `_sentence_units()`) measure the wrapped sentence so `chat_panel._builder_extra_h`/draw
     size the band to it (`_BUILDER_H` removed), keeping a constant `_SENTENCE_PREVIEW_GAP`.
  2. **Blank-strip reclaim** — `_card_bot_off`/`_BUILDER_BOTTOM_PAD` stack the mini-card directly on
     the band; `_input_area_h` no longer reserves the hidden input row's ~70px.
  3. **Collapsible ▾/▴ toggle** — full-width **ACTION … ▾ show / ▴ hide** bar; `is_collapsed()`/
     `toggle_collapsed()`/`apply_auto_collapse(bool)` (manual latches `_user_toggled`); `chat_panel.
     _apply_builder_auto_collapse()` auto-collapses when panel height < `_BUILDER_AUTOCOLLAPSE_H = 620`
     (user-chosen "auto-collapse below threshold").
  4. **Bottom-click UIManager fix** (GUI feedback: dead action button + un-reopenable toggle) — the
     reclaim pushed the builder's button/toggle into the bottom ~62px where the **hidden free-text
     `UIInputText`/`UIFlatButton`, though `visible=False`, were still registered with the UIManager and
     intercepted every click there**. Fix: `_apply_input_visibility` **adds/removes the free-text
     widgets from the UIManager** with visibility; `chat_panel` tracks `_manager`/`_free_text_in_manager`.
     See auto-memory [[feedback_arcade_gui]].

After 50.6: **Phase 51 — Talk to the Dungeon** (roadmap; 50.6 carved the SAY/ASK input seam).
Spec written & finalized: `spec/PHASE_51_TALK_TO_THE_DUNGEON.md`. **In progress** (branch `phase-51`).

---

## Phase 51 — Talk to the Dungeon (in progress, branch `phase-51`)

Spec `spec/PHASE_51_TALK_TO_THE_DUNGEON.md`; decisions locked §3. 10-slice TDD plan (§7).

- **Slice 1 — DONE** (commit `d4770a7`; manifest fields, spec §4.1 / §7.1; campaign suite green 138).
  `CampaignManifest` (`dungeon_daddy/campaign/manifest.py`) gains three optional, backward-compatible
  fields: `dungeon_voice: str | None = None` (personality fed to the LLM), `dungeon_knowledge:
  list[str] = []` (secrets revealed progressively by intimacy), `dungeon_corruption_clock: bool =
  False` (D5 scaffold flag). 2 TDD cycles: defaults; explicit-values + JSON round-trip. No
  validator/seeder changes (optional, not cross-referenced). +2 tests in
  `tests/unit/campaign/test_campaign_manifest.py`.
- **Slice 2 — DONE** (recedable clock engine, spec §4.2 / §7.2; rpg+memory+campaign suites green 922).
  The intimacy clock must move **both ways**, added backward-compatibly: (1) `ClockState.monotonic:
  bool = True` (`rpg/models.py`) — default keeps every existing clock monotonic; intimacy/relationship
  clocks set `False`. (2) signed `tick_clock(clock, delta) -> ClockState` (`rpg/clocks.py`) — clamps
  `filled` to `[0, segments]`; a **monotonic** clock latches `status="completed"` at full (current
  `advance_clock` behavior); a **non-monotonic** clock may recede and **never latches** (thresholds
  read live by callers). (3) `advance_clock` **unchanged** (existing 4 tests are the regression guard).
  (4) migration `016_clock_monotonic.sql` (`clocks.monotonic BOOLEAN DEFAULT true`; auto-discovered by
  the sorted-glob runner). +7 tests (2 model defaults/set-false, 5 engine: +delta increment, monotonic
  latch-at-full, -delta clamp-to-0, non-monotonic no-latch, non-monotonic recede). **Deferred:** repo
  `save_clock`/`get_clocks` do **not** yet read/write `monotonic` (named-column SELECT → new column is
  harmless, reconstructs default-true); wire persistence in the seed slice when `monotonic=False` must
  survive a round-trip.
- **Slice 3 — DONE** (resonance archetype, spec §4.1 / §7.3; rpg+memory suites green 787). Two TDD
  cycles: (1) `"resonance_point"` added to the `ObjectArchetype` Literal (`rpg/models.py`) — a
  `RoomObject` of this archetype has no state-transition interaction (interacting opens the dungeon
  channel, later slices). (2) `build_room_context` (`rpg/room_context.py`) now **derives** the
  `resonance_point` bundle flag from the room's objects via `get_objects_by_room` — `True` when any
  object has the `resonance_point` archetype, OR'd with the explicit `resonance_point` param (kept
  for direct callers). +3 tests (1 model `test_resonance_point_archetype_accepted`, 2 context:
  derived-from-object, false-when-no-resonance-object). **Left out of scope:** the **manifest** object
  `archetype` Literal (`campaign/manifest.py:95`) does NOT yet include `resonance_point` — no seeding
  happens in this pure data slice; add it when the seed slice authors resonance rooms.

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks,
> consequences, and narration. The human player controls the player side: one or more
> player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is
advisory. It may narrate, frame choices, interpret tone, and propose structured world
reactions. It must not directly mutate authoritative state.

---

## Known Failures

**None.** Full unit/integration suite green. The previously-flaky generator eval is resolved
(`26e95a3`, 2026-06-23): evals are excluded from the default run (`addopts = "-m 'not eval'"` —
run with `pytest -m eval`), and `test_generator_level_passes_validation` now mirrors production's
3-retry regenerate-with-errors budget instead of asserting one-shot validity.

---

## Phase History

Phases 42 and earlier: `spec/HISTORY.md`. Recent completed phases:

| Phase | Summary | Spec |
|---|---|---|
| 50.5 — Use Noun on Noun | Grammar → `Verb · Noun · [Target] · Adverb`; `TRANSITIVE_VERBS`; `CombineItems` + migrations `013`/`014`; `GiveItem` validator; `activate` wired; `look` verb; Target dropdown; key-unlock persists; fuse consumed; map level-refresh fix | `spec/PHASE_50_5_USE_ON_GRAMMAR.md` |
| 50 — Hybrid Action Model | Verb·Noun·Adverb action *Card* (input-dual of a proposal); `ActionCard` + `validate_card`; `resolve_card`/`resolve_card_roll` (`rpg/action_resolution.py`); `VnaActionPanel` wired into PlayView (retired `how_chips`); hybrid exit labels via 8-point layout-coord compass (`rpg/exit_labels.py`) | `spec/PHASE_50_HYBRID_ACTION_MODEL.md` (issue #80) |
| 49 — Starting Playbooks | `Playbook` + nested models + `PlaybookLibrary`; `data/playbooks.json` (4 bundled playbooks, kit ability + first pool ability granted at start); `actor_abilities` table + repo CRUD; seed-publish wiring (ratings/tracks/kit/tags/abilities); playbook picker in Seed editor; Character Sheet panel playbook/adverbs/abilities sections | `spec/PHASE_49_STARTING_PLAYBOOKS.md` (issue #77) |
| 48 — Dungeon Navigation | `RoomExit` model + `room_exits` schema; `MoveParty` command; exit-condition validator; level transitions; `DiscoverExit`/`UnlockExit`/`SealExit`/`BlockExit`; room context bundle; Play-mode exit-list panel + fog-of-war map; party-presence gate on `PickUpItem`/`ActivateObject` | `spec/PHASE_48_DUNGEON_NAVIGATION.md` |
| 47 — Room Contents | Items in rooms + interactive objects (state-machine archetypes); `ActivateObject`/`PickUpItem`/`DropItem` commands; `current_room` context block; Campaign Seed editor UI | `spec/PHASE_47_ROOM_CONTENTS.md` |
| 46 — Inventory System | `Item`/`ItemFeature` models; class-kit/dungeon/gear commands; `compute_effective_ratings`; `mark_level_items_inert`; world-reaction item proposals; Character Sheet UI | issue #71 |
| 45 — Campaign Pipeline | Three on-disk libraries; publish pipeline; Library home screen; 4-pill navigation | `spec/PHASE_45_CAMPAIGN_PIPELINE.md` |

Per-session implementation logs are in git history and the auto-memory (`project_phase_status.md`).

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: current/future in `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md`; index at `spec/IMPLEMENTATION_PHASES.md`. Spec-loading rules and skills: `CLAUDE.md` (canonical).
- Roadmap for Phases 51–53 (planned): GitHub Projects `ghostpencil/dungeon-daddy` #1, mirrored in `IMPLEMENTATION_PHASES_33_ONWARDS.md`. Issue bodies hold per-phase detail; a `spec/PHASE_NN_*.md` is written when each phase starts. (Phase 50.5 is **not** on the roadmap and has no issue.)
- Phase 53 (Threat Behavior & Monster Reactions, planned): engine-bounded monster reactions, no enemy turn; bosses escalate via clock thresholds. Design: `spec/MONSTER_REACTION_DESIGN.md`.
- Evals: `pytest -m eval` (live API, paid, non-deterministic); baseline tooling `python tools/run_evals.py` (count-based comparison).
- Playtest reports: `python -m tools.playtest_report <db_path> <campaign_id>` (requires `PYTHONPATH=.`).
- Exit backfill (pre-Phase-48 campaigns): `python -m tools.backfill_room_exits ["<save dir>"] [--dry-run] [--force]`. Close the app first (DuckDB is single-writer). Saves live under `%LOCALAPPDATA%\DungeonDaddy\saves\<name>\`.
- UI icons: `dungeon_daddy/assets/ui/icons/` (white/transparent PNG + SVG source); attribution in `CREDITS.json`. Fetch new ones with the `game-icon-finder` skill.
- `protagonist` actor: `seed_data/campaigns/the-crucible/rpg_seed.json` (use `--seed-pack` + `--force` to reset). Generic `seed_campaign()` no longer creates a placeholder actor.
- **Reseeding a *save* (not a campaign template):** `seed_rpg_state.py` defaults to the `…/DungeonDaddy/campaigns` dir, so to target a real save pass `--campaigns-dir "%LOCALAPPDATA%\DungeonDaddy\saves" --campaign "<Save Name>"`. The `populate_crucible_level*.py` scripts need `PYTHONPATH=.`. Close the app first (DuckDB single-writer). `--force` now **preserves** each actor's `playbook_slug`/`room_id`/`status` (the pack doesn't own them; previously `--force` nulled them, which blanked PC playbooks → action-panel crash). Playbooks are assigned by the publish pipeline / Seed editor, **not** the rpg_seed pack.
- Crucible Level 1 content: `tools/populate_crucible_level1.py` (re-run 2026-06-26) — idempotent upserts of 11 objects, 7 loose items, 4 monsters, 1 NPC, and 3 exits into the live save (`%LOCALAPPDATA%\DungeonDaddy\saves\The Crucible\campaign.duckdb`; close app first). Puzzle chain: R1 journal → R2 lift-warden-key → R2→R4 door (key-gated, permanently unlocked on use) → R3 lift-fuse → R4 Great Lift (fuse-gated, consumed on power-up) → Level 2 r01. **Pinion (R3 NPC) is now seeded `disposition="willing"`** (Slice 10 dialogue gate).
- Creature `disposition` (Phase 50.6 Slice 10): `actors.disposition` column via **migration `015_actor_disposition.sql`** (default `'neutral'`); model `ActorState.disposition` is `Literal["hostile","wary","neutral","willing"]`. **Gates dialogue** — only `willing` is speakable (`is_speakable` in `rpg/action_options.py`); surfaced as the CREATURES status chip. The populate script does **not** apply migrations, so a fresh/old save needs migration 015 applied first (auto on app load via `initialize_schema`, or run it once standalone) before `save_actor(disposition=…)` will work. **Live Crucible save was migrated + re-populated 2026-06-26** (backup `campaign.duckdb.bak-slice10-20260625-165748`).
- Crucible Level 2 content: `tools/populate_crucible_level2.py` (run 2026-06-24) — Great Lift upper landing in r01 (`state=ready`) + open `r01→R4` vertical connector exit (return to Level 1). Re-run to reset.
- Level-crossing exits: `to_level_id` encodes the **0-based list index** of the target level (not the 1-based level ID used for data scoping). `"level:0"` = Level 1 (index 0), `"level:1"` = Level 2 (index 1). `connector_type` must be set for `apply_move_party` to honour `to_level_id`.
- Example campaign manifest: `examples/campaign_manifests/bone-cathedral.json` (validates + seeds cleanly).
- `proposal.applied` / `proposal.rejected` events: call sites must insert `result.rejection_events` into repo with the correct `campaign_id` after `validate_proposal()`.
