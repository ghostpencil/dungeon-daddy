# Visual Design

All constants live in `dungeon_daddy/ui/theme.py`.
Colors are `tuple[int, int, int]` RGB values (0–255).
Alpha variants are `tuple[int, int, int, int]` RGBA.

---

## Color Palette

These are approximate RGB equivalents of the original OKLCH values.
The implementing agent should verify these visually against the web prototype.

```python
# Surfaces — obsidian with violet shift
BG_0  = (28,  26,  40)     # oklch(0.13 0.015 285) — darkest, map background
BG_1  = (38,  35,  54)     # oklch(0.17 0.018 285) — panels
BG_2  = (48,  45,  68)     # oklch(0.21 0.020 285) — elevated surfaces
BG_3  = (60,  56,  84)     # oklch(0.25 0.022 285) — hover states
BG_HI = (74,  70, 104)     # oklch(0.30 0.024 285) — selected / active

# Borders / dividers
LINE_DIM = (58,  54,  80,  178)   # oklch(0.28 0.02 285 / 0.70)
LINE     = (76,  72,  104)         # oklch(0.35 0.025 285)
LINE_HI  = (98,  94,  132)         # oklch(0.45 0.03 285)

# Text
INK_1 = (242, 240, 248)   # oklch(0.96 0.01 285)  — primary text
INK_2 = (204, 202, 218)   # oklch(0.82 0.015 285) — secondary text
INK_3 = (150, 148, 168)   # oklch(0.62 0.02 285)  — muted text
INK_4 = (112, 110, 132)   # oklch(0.48 0.025 285) — disabled / placeholder

# Arcane accents
TEAL       = (60,  210, 195)         # oklch(0.78 0.14 195)
TEAL_DIM   = (80,  148, 140)         # oklch(0.55 0.09 195)
TEAL_GLOW  = (60,  210, 195,  89)    # 35% alpha

VIOLET     = (178, 100, 232)         # oklch(0.68 0.18 305)
VIOLET_DIM = (112,  60, 152)         # oklch(0.48 0.12 305)
VIOLET_GLOW= (178, 100, 232,  89)    # 35% alpha

EMBER      = (230, 158,  48)         # oklch(0.72 0.16 45)  — danger rooms
EMBER_GLOW = (230, 158,  48,  89)

GOLD       = (220, 196,  78)         # oklch(0.82 0.12 85)  — loot accent

# Path colours for loop overlay
PATH_A_COLOR = TEAL
PATH_B_COLOR = VIOLET
PATH_BOTH    = (158, 100, 210)       # blended indigo oklch(0.75 0.12 260)
```

---

## Room Type Colors

Used in map renderers for fill and stroke:

```python
ROOM_COLORS: dict[str, tuple] = {
    "shrine": {"fill": (60, 36, 88),   "stroke": VIOLET},
    "boss":   {"fill": (72, 38, 20),   "stroke": EMBER},
    "vault":  {"fill": (60, 54, 18),   "stroke": GOLD},
    "lair":   {"fill": (58, 40, 18),   "stroke": (160, 110, 50)},
    "stair":  {"fill": (20, 56, 58),   "stroke": TEAL},
    "study":  {"fill": (46, 34, 74),   "stroke": (168, 104, 210)},
    "hall":   {"fill": (44, 42, 60),   "stroke": (120, 116, 148)},
}
```

All rooms always render with their type-specific fill and stroke colours.
There is no separate "unseen" (fog-of-war) style — the GM always sees all rooms.

---

## Typography

Arcade uses `arcade.load_font()` to register TTF files and `arcade.draw_text()`
to render them. Google Fonts TTF files must be bundled with the application.

Required fonts (download and include in `dungeon_daddy/assets/fonts/`):

| Constant | Family | File |
|---|---|---|
| `FONT_SERIF` | IM Fell English | `IMFellEnglish-Regular.ttf` |
| `FONT_SERIF_ITALIC` | IM Fell English Italic | `IMFellEnglish-Italic.ttf` |
| `FONT_SIGIL` | IM Fell English SC | `IMFellEnglishSC-Regular.ttf` | Used for decorative glyphs in the menu bar chrome and section dividers. |
| `FONT_MONO` | JetBrains Mono | `JetBrainsMono-Regular.ttf` |
| `FONT_MONO_MED` | JetBrains Mono Medium | `JetBrainsMono-Medium.ttf` |
| `FONT_UI` | Inter | `Inter-Regular.ttf` |
| `FONT_UI_MED` | Inter Medium | `Inter-Medium.ttf` |
| `FONT_UI_BOLD` | Inter Bold | `Inter-Bold.ttf` |

Register all fonts at application startup before any view is shown.

---

## Font Size Scale

```python
TEXT_XS   = 9
TEXT_SM   = 10
TEXT_BASE = 12
TEXT_MD   = 13
TEXT_LG   = 14
TEXT_XL   = 15
TEXT_2XL  = 18
TEXT_3XL  = 19
TEXT_4XL  = 22
```

---

## Spacing & Radii

```python
PAD_XS  = 4
PAD_SM  = 8
PAD_MD  = 12
PAD_LG  = 14
PAD_XL  = 18

RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 10
RADIUS_2XL= 14
```

---

## Panel Widths

```python
PANEL_TREE_WIDTH      = 240   # Design Mode left panel
PANEL_INSPECTOR_WIDTH = 320   # Design Mode right panel
PANEL_CHAT_WIDTH      = 440   # Play Mode left panel
PANEL_STEPPER_WIDTH   = 70    # Play Mode right rail
CHROME_MENUBAR_HEIGHT = 26
CHROME_TITLEBAR_HEIGHT= 44
```

---

## Drawing Utilities

`dungeon_daddy/ui/theme.py` should also export helper functions used across renderers:

```python
def draw_rounded_rect(
    x: float, y: float, width: float, height: float,
    radius: float, color: tuple, border_color: tuple | None = None,
    border_width: float = 1,
) -> None:
    """
    Arcade does not provide a native rounded-rect primitive.
    Implement using arcade.draw_polygon_filled() with a point list that
    approximates rounded corners via 8-point octagon clipping, or use
    arcade.draw_rect_filled() with a separate arc pass for corners.

    Recommended approach: build a ShapeElementList with arcade.create_rectangle_filled()
    and four quarter-circle shapes (arcade.create_arc_filled()) at each corner.
    Cache the ShapeElementList when color and size are unchanged.
    """

def draw_kicker(
    text: str, x: float, y: float,
    anchor_x: str = "left",
) -> None:
    """Draw FONT_MONO, TEXT_SM, INK_2, uppercase label.
    When anchor_x == 'left', draws a 2×14 px TEAL accent bar 6 px left of x."""
    ...

def draw_chip(
    text: str, cx: float, cy: float,
    color: str = "default",  # "default" | "teal" | "violet" | "ember" | "gold"
) -> None:
    """Draw a small rounded pill label."""
    ...
```
