# Phase 42 — Campaign Authoring UI

**Status: IN PROGRESS**

### Slice Progress

- [x] Slice 1 — CampaignView state machine (`_init_state`, `load_manifest`, `set_active_section`)
- [x] Slice 2 — Actor CRUD
- [x] Slice 3 — Clock CRUD
- [x] Slice 4 — Memory seed & room threat CRUD
- [x] Slice 5 — Validation
- [x] Slice 6 — Save/load
- [x] Slice 7 — Panel hit-test logic
- [x] Slice 8 — Rendering layer (draw methods, CampaignEditPanel, view lifecycle, 3-pill chrome)
**Branch:** `phase-42-campaign-authoring-ui`

---

## Goal

Add **Campaign Mode** — a third top-level mode in the Dungeon Daddy app (alongside Design and Play) that lets the GM load, browse, and fully author campaign manifests with full CRUD for all entity types.

The UI must feel like a **campaign tome or grimoire**, not a database editor. Rich serif typography, thematic color coding per entity type, card-based layout rather than rows-in-a-table.

The campaign module (manifest schema, validator, patcher) was built in Phases 40–41. This phase adds the UI surface on top of it.

---

## Layout & Information Architecture

Three-panel layout, matching the existing Design Mode approach.

```
┌──────────────────────────────────────────────────────────────────┐
│  DUNGEON DADDY          [DESIGN]  [CAMPAIGN]  [PLAY]             │  ← title bar (44px)
├──────────────────────────────────────────────────────────────────┤
│ CAMPAIGN     │  PLAYER SIDE              │  EDIT ACTOR           │
│              │ ────────────────── + ADD  │ ─────────────────     │
│ ✦ The Bone   │  ┌────────────────────┐   │  Name                 │
│   Cathedral  │  │ Valeria            │   │  [Valeria        ]    │
│              │  │ PC  ● active       │   │                       │
│ ──────────── │  │ Inquisitor sworn   │   │  Type                 │
│ ✦ PLAYER     │  │ fight ●● sway ●●  │   │  [PC] [NPC] [MONSTER] │
│   SIDE   [2] │  └────────────────────┘   │                       │
│ ⚔ MONSTERS   │  ┌────────────────────┐   │  Concept              │
│   [3]        │  │ Osric              │   │  [Grave-robber…  ]    │
│ ◈ NPCS   [0] │  │ PC  ● active       │   │                       │
│ ⬡ FACTIONS   │  │ move ●● tinker ●● │   │  Action Ratings       │
│   [1]        │  └────────────────────┘   │  fight  [2] [+][-]    │
│ ◷ CLOCKS [3] │                           │  move   [1] [+][-]    │
│ ⚠ THREATS[3] │                           │                       │
│ ✦ LORE   [3] │                           │  [Save]  [Cancel]     │
│ ✓ VALIDATE   │                           │                       │
│              │                           │                       │
│ [Load] [New] │                           │                       │
│ [Save]       │                           │                       │
└──────────────┴───────────────────────────┴───────────────────────┘
```

**Panel widths:**
- Left nav: 220px
- Center list: flexible (`w − 220 − 300`)
- Right edit: 300px

---

## Visual Design

### Title Bar — Three Mode Pills

Replace the single mode badge with three pill buttons right-aligned in the title bar:

```
[DESIGN]  [CAMPAIGN]  [PLAY]
```

- **Active pill:** filled accent background, label in `BG_1`
  - DESIGN → `VIOLET` fill
  - CAMPAIGN → `GOLD` fill _(authoring / lore richness)_
  - PLAY → `TEAL` fill
- **Inactive pills:** `BG_2` fill, `LINE` border, `INK_3` label
- Pill size: ~90×22px, 8px gap. Total block: `3×90 + 2×8 = 286px`, right-aligned.
- Click detection: each view tracks pill rects in `on_mouse_press`, calls `self.window.switch_mode(mode)`.
- Update DesignView and PlayView to use the same three-pill approach.

### Left Nav Panel

| Element | Style |
|---|---|
| Header "CAMPAIGN" kicker | `BG_2` header 38px, `draw_kicker()` |
| Campaign title | IM Fell English, `TEXT_LG`, `INK_1` |
| No campaign loaded | `INK_4` italic placeholder |
| Load / New buttons | Small teal outlined pills, side by side |
| Section rows (32px each) | `BG_1` inactive; `BG_HI` + `GOLD` left accent bar active |
| Section glyph + name | Glyph + mono `TEXT_SM` |
| Count badge | `draw_chip()` right-aligned |
| Save button (bottom) | Teal pill; `INK_4` / disabled when not dirty |

**Sections (in order):**

| Glyph | Label | Manifest field |
|---|---|---|
| ✦ | PLAYER SIDE | `player_side` + actors |
| ⚔ | MONSTERS | `world_actors` type ∈ {monster, dungeon, dungeon_presence} |
| ◈ | NPCS | `world_actors` type == npc |
| ⬡ | FACTIONS | `factions` |
| ◷ | CLOCKS | `clocks` |
| ⚠ | THREATS | `room_threats` |
| ✦ | LORE | `memory_seeds` |
| ✓ | VALIDATION | runs validator on demand |

### Center List — Item Cards

All cards: `BG_2` background, 1px `LINE` border, `RADIUS_MD` corners, `PAD_MD` inset, 8px gap between cards.

**Actor card:**
- Name: IM Fell English, `TEXT_2XL`, `INK_1`
- Type chip (`draw_chip()`): PC=`VIOLET`, NPC=`TEAL`, MONSTER=`EMBER`, FACTION=`GOLD`
- Status dot: ● `TEAL`=active, ● `INK_4`=inactive, ● `EMBER`=dead/lost
- Concept line: italic serif `TEXT_BASE`, `INK_3`, one line truncated
- Action ratings: tiny mono chips `fight●●○ move●●●` along card bottom

**Clock card:**
- Label: serif `TEXT_2XL`
- Segment pips: row of circles — filled=`TEAL` dot, empty=`BG_3` circle (4px dia, 3px gap)
- Chips: `clock_level` (`VIOLET`) + `category` (`GOLD` if set)
- Stakes snippet: italic `INK_3`

**Room threat card:**
- Location slug: mono `TEXT_SM`, `INK_3`, uppercase
- Description: serif `TEXT_BASE`
- Related slugs: `TEAL` actor chips, `VIOLET` clock chips

**Memory seed / Lore card:**
- Text in IM Fell English italic, `TEXT_BASE`, `INK_2`
- Left 2px `GOLD` vertical accent bar (blockquote style)
- `BG_3` background (slightly lighter, "quote" feel)

**Delete affordance:** Small `EMBER` "✕" revealed on card hover via `on_mouse_motion` tracking (`_hovered_card_index`).

**Add button:** Teal pill "+ ADD" right-aligned in the center panel header.

### Right Edit Panel

- Header: "EDIT ACTOR" / "NEW CLOCK" / "EDIT LORE" — kicker on `BG_2`
- No item selected: serif italic "Select an item to edit" in `INK_4`, vertically centered
- Form sections separated by `draw_kicker()` labels

**Actor form fields:**
- `display_name` — `UIInputText`
- `slug` — `UIInputText` (mono font), auto-filled from name, editable
- `actor_type` — row of chip-style `UIFlatButton`s (PC / NPC / MONSTER / DUNGEON / FACTION / PRESENCE)
- `status` — chip row (active / inactive / dead / absorbed / lost)
- `concept` — multiline `UIInputText`, 3 lines tall
- **Action Ratings** section: each action key → label + number display + `[+]` `[−]` `UIFlatButton`s
- `tags` — existing tags as inline chips with `×`; text input to add new

**Clock form fields:**
- `label`, `slug` — text inputs
- `segments` — number input + live pip preview
- `filled` — number input capped to segments + live pip preview
- `clock_level` — chip row
- `category` — text input
- `stakes`, `completion_effect` — multiline text inputs
- `action_tags` — tag input
- `visible_to_player` — toggle chip [YES] / [NO]

**Memory seed form:** Single large multiline `UIInputText`.

**Room threat form:**
- `location_slug` — text input
- `description` — multiline text
- `related_actor_slugs`, `related_clock_slugs` — tag inputs

**Form footer:** `[SAVE]` (teal) + `[CANCEL]` (default) `UIFlatButton`s, fixed at bottom.

---

## File Plan

### New files

| File | Purpose |
|---|---|
| `dungeon_daddy/views/campaign_view.py` | Main `arcade.View`; owns manifest state, coordinates panels |
| `dungeon_daddy/ui/panels/campaign_nav_panel.py` | Left section navigator (draw + hit-test) |
| `dungeon_daddy/ui/panels/campaign_list_panel.py` | Center item card list (draw + scroll + hover) |
| `dungeon_daddy/ui/panels/campaign_edit_panel.py` | Right edit form (`UIManager` widgets) |
| `tests/unit/ui/test_campaign_view.py` | Business logic tests (no Arcade rendering) |
| `tests/unit/ui/test_campaign_panels.py` | Panel state and hit-test tests (Arcade mocked) |

### Modified files

| File | Change |
|---|---|
| `dungeon_daddy/ui/chrome.py` | `draw_title_bar` → 3-pill mode switcher; add `GOLD` import |
| `dungeon_daddy/window.py` | Add `_campaign_view`, `switch_to_campaign()`, update `switch_mode()`, `_build_menu()` |
| `dungeon_daddy/views/design_view.py` | Update title bar call to render 3 pills |
| `dungeon_daddy/views/play_view.py` | Update title bar call to render 3 pills |

---

## TDD Order — Vertical Slices

Each slice: RED → GREEN → REFACTOR before moving on.

### Slice 1 — CampaignView state machine
`tests/unit/ui/test_campaign_view.py`
- No manifest loaded → `active_section` is None, `is_dirty` is False
- `load_manifest(m)` sets manifest, clears dirty, auto-selects first section
- `set_active_section("clocks")` changes section

### Slice 2 — Actor CRUD
- `add_actor(actor)` appends to `world_actors` (or `factions`), sets dirty
- `update_actor(slug, display_name="X")` patches in place
- `remove_actor(slug)` removes from world_actors or factions
- `set_player_side(["slug-a"])` updates manifest

### Slice 3 — Clock CRUD
- `add_clock(clock)` appends, sets dirty
- `update_clock(slug, filled=3)` patches
- `remove_clock(slug)` removes

### Slice 4 — Memory seed & room threat CRUD
- `add_memory_seed(text)` appends, sets dirty
- `remove_memory_seed(index)` removes by index
- `add_room_threat(threat_dict)` / `remove_room_threat(index)`

### Slice 5 — Validation
- `run_validation()` calls `campaign.validator.validate()`, stores result
- Returns list of `ManifestError` objects; sets `_validation_result`

### Slice 6 — Save/load
- `save_to_path(path)` → writes valid JSON parseable back to `CampaignManifest`
- `load_from_path(path)` → sets manifest, clears dirty

### Slice 7 — Panel hit-test logic (no rendering)
- `CampaignNavPanel.section_at(x, y)` returns section key or None
- `CampaignListPanel.item_at(x, y)` returns item index or None (scroll-offset-aware)
- `CampaignListPanel.delete_zone_at(x, y)` returns item index when in card's ✕ region

---

## Reused Patterns & Utilities

- `draw_kicker(text, x, y)` — section header labels (`theme.py`)
- `draw_chip(text, cx, cy, color)` — type badges, status chips (`theme.py`)
- `draw_rounded_rect(...)` — card backgrounds (`theme.py`)
- `_make_tk_root()` + `tk.filedialog.askopenfilename()` — file picker for Load (existing Tkinter dialog pattern in `window.py`)
- `CampaignManifest`, `ActorManifest`, `ClockManifest` from `dungeon_daddy/campaign/manifest.py`
- `validate()` from `dungeon_daddy/campaign/validator.py`
- `UIInputText`, `UIFlatButton` via `arcade.gui` (established pattern in `design_view.py`)
- Scissor-clip scrolling pattern from `chat_panel.py`
- `_overlay_btn_style()` pattern from `design_view.py` for form buttons

---

## Verification Checklist

1. `pytest tests/unit/ui/test_campaign_view.py` — all slices green
2. `pytest tests/unit/ui/test_campaign_panels.py` — panel logic green
3. `pytest` — all 2266+ prior tests still passing
4. Launch `python -m dungeon_daddy`, click `[CAMPAIGN]` pill in title bar
5. Load `examples/campaign_manifests/bone-cathedral.json`
6. Verify all sections show correct item counts
7. Click PLAYER SIDE → Valeria + Osric cards with type chips and ratings
8. Click CLOCKS → clock cards with segment pips
9. Click `+ ADD` → empty form appears in right panel
10. Fill in a new actor, click `[SAVE]` → card appears in list
11. Click existing card, edit name, `[SAVE]` → card updates
12. Click `✕` on a card → card removed, dirty flag set, `[Save]` button activates
13. Click VALIDATION → errors in EMBER if any, TEAL "✓" banner if clean
14. Click `[Save]` → manifest written to file
15. Switch to DESIGN or PLAY → returns to respective view correctly
