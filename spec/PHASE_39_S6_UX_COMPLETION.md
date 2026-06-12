# Phase 39.S6 — UX Completion: Actor Switcher + In-Chat Action Card

## Status

STABILIZATION — complete before Phase 40.

---

## Goal

Close the remaining UX gaps found during manual testing of Phase 39:

1. Classifier false positives and missing keywords (fix done 2026-06-12)
2. No way to switch actors from the chat area
3. Pending-intent confirmation uses a chip row swap that feels disconnected from the framing message

---

## Context

Phase 39.S1–S5 built `set_pending_chips()` to replace the static chip row with action chips when
a pending intent is awaiting confirmation. Manual testing revealed:

- The chip row is visually detached from the framing message above it — the player has to look
  in two places (framing text in the chat area, chips in the input area).
- There is no actor switcher in the chat area; the mini card is read-only.
- The classifier matched `"run"` inside `"runes"`, triggering `move` instead of `study`.

---

## Design Decision: In-Chat Action Card

Replace the chip-swap approach with an **action card** rendered inline in the chat scroll area.
The card appears as a special message bubble immediately after the framing text message.

```
┌─────────────────────────────────────────┐
│ ◆ Framing                               │
│ Suggested: [STUDY] [SENSE]              │
│ Click an action below, or send text...  │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ Talvas — study the runes on...      │ │
│ │  [ STUDY ]  [ SENSE ]  [ No Roll ] │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

After resolution, the chosen button is highlighted in teal and the others are dimmed. The card
becomes inert (no further clicks processed).

The static chip row in the input area is **never replaced** — it always shows `_CHIPS_PLAY`.
`set_pending_chips()` and `_pending_chips` are removed from the pending intent flow.

**Why this is better than the chip row:**
- Choices appear next to the context that produced them.
- The card can show the actor name and a truncated echo of the intent.
- The input area stays clean and consistent.

---

## Tasks

### 39.S6.1 — Classifier fix  ✅ DONE (2026-06-12)

**What changed:**
- `dungeon_daddy/rpg/classifier.py`: switched from `kw in lowered` (substring) to
  `re.search(r'\b' + re.escape(kw) + r'\b', lowered)` (whole-word). Pre-compiled patterns
  stored in `_COMPILED` for performance.
- Expanded `"study"` keywords: added `"study"`, `"studies"`, `"examine"`, `"rune"`, `"runes"`,
  `"inscription"`.
- Removed `"endure mentally"` multi-word entry from `"focus"` (phrase matching was unreliable
  with whole-word regex; replaced with single-word terms).
- 4 new tests in `tests/unit/rpg/test_intent_classifier.py`.

---

### 39.S6.2 — Actor switcher in mini card row

**Behavior:**
- When `PlayerActionState.has_multiple_actors` is True, render `<` and `>` arrows flanking
  the actor name in the mini card row.
- Click `<` → `select_prev_actor()`, click `>` → `select_next_actor()`.
- After switch: `PlayView._refresh_chat_mini_card()` updates the display.
- Arrows are hidden (not rendered, not clickable) when `awaiting_confirmation=True` — actor
  must not change mid-intent.

**ChatPanel API additions:**
```python
def set_actor_switch_callback(self, fn: Callable[[str], None]) -> None:
    """fn receives "prev" or "next"."""

def set_has_multiple_actors(self, flag: bool) -> None:
    """Controls whether < > arrows are shown in the mini card row."""
```

**ChatPanel internals:**
- `_actor_switch_callback: Callable[[str], None] | None`
- `_has_multiple_actors: bool`
- `_mini_card_prev_rect: tuple | None` — hit area for `<`
- `_mini_card_next_rect: tuple | None` — hit area for `>`
- `draw()` / `_draw_mini_card()`: render arrows when `_has_multiple_actors and not _pending_chips`
  (re-use `_pending_chips` as the "awaiting" proxy, or add an explicit flag)
- `on_mouse_press()`: check arrow rects before chip rects

**PlayView wiring:**
- In `__init__`: `self._chat.set_actor_switch_callback(self._on_actor_switch)`
- New method `_on_actor_switch(direction: str)`:
  ```python
  def _on_actor_switch(self, direction: str) -> None:
      if self._action_state.awaiting_confirmation:
          return
      if direction == "prev":
          self._action_state.select_prev_actor()
      else:
          self._action_state.select_next_actor()
      self._refresh_chat_mini_card()
  ```
- `_load_player_actors()`: after roster is set, call
  `self._chat.set_has_multiple_actors(self._action_state.has_multiple_actors)`
- `_refresh_chat_mini_card()`: also call `set_has_multiple_actors` after each refresh

---

### 39.S6.3 — In-chat action card

#### ChatPanel API additions

```python
def add_action_card(
    self,
    actor_name: str,
    intent_text: str,
    action_keys: list[str],
) -> None:
    """Add an interactive action card to the message list.
    Only one card is active at a time; calling this again deactivates the previous one."""

def resolve_active_card(self, chosen_label: str) -> None:
    """Mark the active card as resolved. chosen_label is shown in teal; others dim.
    No further clicks are processed on the card."""
```

#### ChatPanel internals

Messages are stored as `ChatMessage` objects. Add a new role `"action_card"` with the card
data stored alongside:

```python
# New private dataclass (internal to chat_panel.py)
@dataclasses.dataclass
class _ActionCardData:
    actor_name: str
    intent_text: str          # truncated to ~60 chars for display
    action_keys: list[str]    # e.g. ["STUDY", "SENSE"]
    resolved_label: str | None = None   # set after resolution
```

Store cards in a parallel `_action_cards: dict[int, _ActionCardData]` keyed by message index.
Track `_active_card_index: int | None` — the index of the card currently accepting clicks.

**Hit area tracking:**
```python
_active_card_button_rects: list[tuple[str, tuple[float, float, float, float]]]
# list of (label, (x, y, w, h)) — rebuilt each draw() call for the active card
```

**Rendering (`draw()`):**
- For each message with role `"action_card"`, call `_draw_action_card(msg_index, y_offset)`.
- Card bubble: `BG_2` background, `LINE` border, slightly wider than a standard bubble.
- Inside: actor name (teal, small), intent echo (INK_3, truncated), button row.
- Button row: each action key as a rounded pill (`BG_3` bg, `LINE` border, `INK_2` text).
  "No Roll" uses `INK_4` to de-emphasise.
- Resolved state: chosen label pill uses `TEAL` border + text; others `INK_4`; no pointer cursor.

**Hit testing (`on_mouse_press`):**
```python
# Adjust y for scroll offset, then check _active_card_button_rects
for label, (bx, by, bw, bh) in self._active_card_button_rects:
    if bx <= x < bx + bw and by <= y < by + bh:
        if self._chip_click_callback:
            self._chip_click_callback(label)
        return
```

Re-use `_chip_click_callback` — the label received is the same format the existing
`_on_pending_chip_click` already handles.

#### PlayView changes

When pending intent is classified (`_on_chat_send`, suggestions branch):
1. Add the framing system message (keep as-is for chat log context).
2. Call `self._chat.add_action_card(actor_name, text, [k.upper() for k in suggestions[:3]] + ["No Roll"])`.
3. **Remove** `self._chat.set_pending_chips(...)` call.
4. Keep `self._chat.set_chip_click_callback(self._on_pending_chip_click)` — still needed.

When intent resolves (both `_do_action_from_chip` and `_do_no_roll_from_chip`):
1. Call `self._chat.resolve_active_card(label)` before `self._chat.set_pending_chips(None)`.
2. Remove `self._chat.set_pending_chips(None)` calls (chips are no longer swapped).

When intent resolves via text-send paths (`_on_chat_send`, action_key branch and
awaiting_confirmation branch):
1. Call `self._chat.resolve_active_card("...")` with appropriate label.
2. Remove `self._chat.set_pending_chips(None)` calls.

---

### 39.S6.4 — Remove pending_chips from pending intent flow

After the action card is wired, the `_pending_chips` / `set_pending_chips` path is no longer
used for pending intent. Options:

- **Keep** `set_pending_chips` API but stop calling it from the intent path (safest — keeps
  tests passing with minimal churn).
- **Remove** `set_pending_chips` entirely if no other caller exists.

Preferred: keep the API but stop calling it from PlayView's intent path. Update
`test_play_view_pending_intent.py` slices 8, 9, 11 which assert `set_pending_chips` was called.

---

### 39.S6.5 — Test updates

**`tests/unit/ui/test_chat_panel.py`** — new tests:
- `add_action_card` stores card data and sets active card index
- `resolve_active_card` sets resolved_label on the correct card
- `on_mouse_press` within button rect calls chip_click_callback with label
- `on_mouse_press` after card resolved does not fire callback
- `set_has_multiple_actors` / `set_actor_switch_callback` stored correctly

**`tests/unit/views/test_play_view_pending_intent.py`** — update/add:
- Slice 8: `add_action_card` called (not `set_pending_chips`) on classification
- Slice 9: `resolve_active_card` called after chip click
- Slice 11: `resolve_active_card` called on text-send resolve paths
- New slice: actor switcher callback wired; switching disabled when awaiting
- New slice: `set_has_multiple_actors` called when roster loaded

---

## Exit Criteria

- [ ] "Talvas studies the runes on the floor" → `STUDY` suggested (not `MOVE`)
- [ ] Typing actionable text shows an action card in the chat scroll area
- [ ] Action card shows actor name, truncated intent, and action buttons
- [ ] Clicking an action button on the card resolves immediately (no second send)
- [ ] Clicking "No Roll" on the card fires narration, no RPG resolution
- [ ] After resolution the card is inert: chosen action shown in teal, others dimmed
- [ ] Static chips in the input area are never replaced during pending intent
- [ ] Actor mini card shows `<` `>` arrows when multiple actors are loaded
- [ ] Clicking `<` / `>` cycles to the previous/next actor and updates the mini card
- [ ] Arrows are hidden while a pending intent is awaiting confirmation
- [ ] All 2145+ tests pass

---

## Implementation Order

1. 39.S6.2 first (actor switcher) — self-contained ChatPanel + PlayView change, no card logic
2. 39.S6.3 + 39.S6.4 together — card rendering and wiring are coupled
3. 39.S6.5 — test updates follow implementation

---

## Notes

- The scroll offset (`_scroll_offset`) must be subtracted from the raw mouse `y` when hit-testing
  card button rects. Card rects are computed in draw-space; mouse events are in screen-space.
- Only one card is active at a time. `add_action_card` deactivates any previous card before
  setting the new one.
- `_active_card_button_rects` is rebuilt each `draw()` call (not cached) since scroll position
  changes between frames.
- Keep card button height consistent with chip row height (`_CHIP_CY_OFF` reference) for
  visual alignment.
- Read `spec/TESTING.md` before writing any new tests.
