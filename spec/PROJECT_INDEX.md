# Dungeon Daddy — Project Index

## Phase

Phase: 39.S6 — UX Completion (Stabilization)
Status: **COMPLETE** — All 39.S6 tasks done (2026-06-12)

Branch: `phase-39-intent-framing`

---

## Product Direction

> Dungeon Daddy controls the world, dungeon, monsters, NPCs, secrets, clocks, consequences, and narration.
> The human player controls the player side: one or more player-controlled actors and the actions they attempt.

**Core authority rule:** The RPG engine and memory layer are authoritative. The LLM is advisory. It may narrate, frame choices, interpret tone, and propose structured world reactions. It must not directly mutate authoritative state.

---

## Phase 39 — Stabilization Required

### Goal

Let Dungeon Daddy help frame player intent into an RPG action while preserving player agency and deterministic authority.

Full spec: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` — search for "Phase 39".

### Tasks

- [x] 39.1 — `PendingIntent` model (actor_id, raw_text, suggested_action_keys, suggested_primary_action, stakes_text, status)
- [x] 39.2 — Deterministic intent classifier (keyword → ranked action suggestions)
- [x] 39.3 — Framing UI in chat (pending intent → suggested chips, no resolve yet)
- [x] 39.4 — Confirmation path (chip click → `ActionRequest` → RPG resolution → world reaction → narration)
- [x] 39.5 — No-roll path (intent → plain DM narration, no action resolution)

### Exit Criteria (original)

- [x] Natural language chat can create a pending intent
- [x] System proposes action choices without resolving automatically
- [x] Player confirmation is required before any RPG action roll
- [x] Confirmed action uses the authoritative RPG/world reaction path
- [x] No-roll path remains available
- [x] LLM does not directly resolve player intent
- [x] Tests cover classifier, confirmation, cancellation, and no-roll paths
- [x] Smoke test shows a full natural-language intent → suggested action → confirmed roll → consequence → narration flow

### Known UX Gap (found 2026-06-11) — STABILIZATION needed before Phase 40

**The confirmation chips in chat are text-only, not clickable.** The full loop does not work from chat alone.

What was built:
- `classify_intent()`, `PendingIntent`, state machine — all correct.
- `dungeon_daddy/ui/action_chips.py` (`build_action_chips`) — built, tested, **never rendered in chat**.
- `dungeon_daddy/ui/actor_mini_card.py` (`build_actor_mini_card`) — built, tested, **never rendered in chat**.
- Framing message in chat shows `[STUDY] [SENSE]` as text, then says "Open RPG panel → click STUDY" — this redirects the player to the right panel, defeating the chat-centered design.
- Tests pass because they call `view._action_state.select_action("study")` directly (no real UI counterpart).

What's still missing:
1. **Dynamic suggestion chips in the chat input area** — when `awaiting_confirmation=True`, the static quick-chips row (`_CHIPS_PLAY`) must be replaced with the pending intent's suggested actions + "No Roll".
2. **Chip click callback in ChatPanel** — clicking a suggestion chip must call back into PlayView with the action key and trigger immediate resolution (no second send required).
3. **Fix `_format_intent_framing`** — remove the "Open RPG panel" instruction; the framing message must be self-contained in chat.
4. **Actor mini card in chat** — render `build_actor_mini_card()` above the chips row (actor name + compact stress summary). The data model exists; the rendering does not.

### Stabilization Tasks (Phase 39 — do before Phase 40)

- [x] **39.S1** — `ChatPanel.set_pending_chips(chips: list[str] | None)`: when not None, override the static quick-chips row with the given labels; restore static chips when None. Chips must be clickable (not text). Add a `set_chip_click_callback(fn)` that receives the chip label on click.
- [x] **39.S2** — `PlayView` wiring: when pending intent is set, call `self._chat.set_pending_chips([...suggested labels..., "No Roll"])`. On chip click: if label is "No Roll" → no-roll path; otherwise map label → action key → `action_state.select_action(key)` → `_run_chat_action()` immediately (no second send needed). When intent is resolved or cancelled, call `self._chat.set_pending_chips(None)` to restore static chips.
- [x] **39.S3** — Fix `_format_intent_framing`: remove "Open RPG panel" instruction. New copy: "Click an action below, or send text to skip the roll."
- [x] **39.S4** — Wire actor mini card: render `build_actor_mini_card()` data in the chat input area above the chips row (actor name + stress bars). Update when the active actor changes. `INPUT_AREA_H` expanded to 122 to accommodate the 18px mini card row.
- [x] **39.S5** — Update `test_play_view_pending_intent.py` tests for the new chip-click path. Smoke test update deferred to next session.

### Implementation Notes

- `ChatPanel._chip_rects` already tracks chip hit areas for click detection. `set_pending_chips` should follow the same pattern.
- `ChatPanel` already has a send callback; add a separate chip-click callback so the two paths stay distinct.
- The actor mini card render area is the row directly above the chips row, within `INPUT_AREA_H`. Check `_CHIP_CY_OFF` to find the right y coordinates.
- All changes are UI-only (no RPG/memory model changes). Keep strictly within the stabilization scope.

---

## Phase 39.S6 — UX Completion

Full spec: `spec/PHASE_39_S6_UX_COMPLETION.md`

### Tasks

- [x] **39.S6.1** — Classifier fix: word boundary matching; expanded study keywords (2026-06-12)
- [x] **39.S6.2** — Actor switcher: `< Name >` arrows in mini card row; disabled during pending intent (2026-06-12)
- [x] **39.S6.3** — In-chat action card: replaces chip-swap; rendered inline in scroll area; clickable buttons; inert after resolution (2026-06-12)
- [x] **39.S6.4** — Remove `set_pending_chips` from pending intent flow (keep API, stop calling it) (2026-06-12)
- [x] **39.S6.5** — Test updates: ChatPanel card rendering/hit testing; PlayView wiring (2026-06-12)

### Exit Criteria

- [x] "Talvas studies the runes on the floor" → `STUDY` suggested (not `MOVE`)
- [x] Typing actionable text shows an action card inline in chat
- [x] Clicking an action button on the card resolves immediately
- [x] After resolution the card is inert: chosen action teal, others dimmed
- [x] Static chips in the input area never replaced during pending intent
- [x] `< Name >` arrows visible when multiple actors; hidden while awaiting confirmation
- [x] All tests pass (2018 unit + 149 integration = 2167 total, 2026-06-12)

### Post-S6 UI polish (same session, 2026-06-12)

- Action card buttons: hover highlight (`BG_HI` fill + `LINE_HI` border); FONT_MONO for predictable widths
- "No Roll" text no longer cut off (wider padding: 8px, 7px/char monospace)
- Action card bubble height increased 80→96px
- Stress track squares now labelled with 3-char key prefix (e.g. `bod`, `com`)
- Actor name truncated to 16 chars in mini card row to preserve space for stress bars
- `ChatPanel.on_mouse_motion` added; routed from `PlayView.on_mouse_motion`
- 2023 unit tests passing after polish

### Character card (2026-06-12, second session)

- Replaced mini card + static play chips with a full character card in `ChatPanel`
  - Portrait placeholder (dark box, `◆` icon), character name, 3×3 action ratings, 4 stress tracks (2×2)
  - Play mode `INPUT_AREA_H` expanded 122 → 176 px; `_CHAR_CARD_H = 96`
  - Removed `_CHIPS_PLAY` static suggestions; play mode chips only shown when `_pending_chips` is set
  - Fixed-position `<` / `>` carousel arrows; wrapping already worked via modulo
  - Fixed stress label/box overlap (`_LBL_W` 22→30, `_SQ_GAP` 1→2)
- Added `actions: dict[str, int]` to `ActorMiniCardData` / `build_actor_mini_card`
- Fixed `seed_data/campaigns/the-crucible/rpg_seed.json`: added `protagonist` actor so `--force` resets its stress tracks
- Removed stale `actor:the-crucible:protagonist` (string-ID) row from DB

---

## Known Failures

None (test suite passes).

---

## Previous Phases

Phase 38 and earlier are complete. Full history in `spec/HISTORY.md`.

Last recorded test count: **653 unit (ui+rpg subset) passing** (2026-06-12, second session). Full suite count from earlier: 2023 unit + 149 integration = 2172.

---

## Resume Notes (2026-06-12)

### Phase 39 complete. Next: Phase 40.

Read `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` for Phase 40 spec before starting.

`protagonist` actor is now in `rpg_seed.json` (The Crucible). Running `--force` will reset its stress tracks. The old string-ID duplicate row has been removed from the DB.

---

## Notes

- Provider: OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set.
- Phase specs: `spec/IMPLEMENTATION_PHASES_33_ONWARDS.md` (current); index at `spec/IMPLEMENTATION_PHASES.md`.
- Spec loading rules and skills: `CLAUDE.md` (canonical source).
