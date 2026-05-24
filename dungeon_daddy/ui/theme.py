"""
Visual design constants for Dungeon Daddy.
All colors are RGB tuple[int, int, int] or RGBA tuple[int, int, int, int].
All values live here; no other module hard-codes colors, fonts, or sizes.
"""
from __future__ import annotations

import arcade

# ---------------------------------------------------------------------------
# Color palette — obsidian surfaces with violet shift
# ---------------------------------------------------------------------------

BG_0  = (28,  26,  40)      # darkest — map background
BG_1  = (38,  35,  54)      # panels
BG_2  = (48,  45,  68)      # elevated surfaces
BG_3  = (60,  56,  84)      # hover states
BG_HI = (74,  70, 104)      # selected / active

# Borders / dividers
LINE_DIM = (58,  54,  80, 178)   # 70% alpha
LINE     = (76,  72, 104)
LINE_HI  = (98,  94, 132)

# Text
INK_1 = (242, 240, 248)    # primary
INK_2 = (204, 202, 218)    # secondary
INK_3 = (150, 148, 168)    # muted
INK_4 = (112, 110, 132)    # disabled / placeholder

# Arcane accents
TEAL       = (60,  210, 195)
TEAL_DIM   = (80,  148, 140)
TEAL_GLOW  = (60,  210, 195,  89)   # 35% alpha

VIOLET     = (178, 100, 232)
VIOLET_DIM = (112,  60, 152)
VIOLET_GLOW= (178, 100, 232,  89)

EMBER      = (230, 158,  48)
EMBER_GLOW = (230, 158,  48,  89)
AMBER      = EMBER

GOLD       = (220, 196,  78)

# Path colors for loop overlay
PATH_A_COLOR = TEAL
PATH_B_COLOR = VIOLET
INDIGO       = (158, 100, 210)   # blended oklch(0.75 0.12 260)
PATH_BOTH    = INDIGO

# ---------------------------------------------------------------------------
# Room type colors
# ---------------------------------------------------------------------------

ROOM_COLORS: dict[str, dict[str, tuple]] = {
    "shrine": {"fill": (60,  36,  88), "stroke": VIOLET},
    "boss":   {"fill": (72,  38,  20), "stroke": EMBER},
    "vault":  {"fill": (60,  54,  18), "stroke": GOLD},
    "lair":   {"fill": (58,  40,  18), "stroke": (160, 110,  50)},
    "stair":  {"fill": (20,  56,  58), "stroke": TEAL},
    "study":  {"fill": (46,  34,  74), "stroke": (168, 104, 210)},
    "hall":   {"fill": (44,  42,  60), "stroke": (120, 116, 148)},
}

# Unseen room colors (not yet visited)
ROOM_UNSEEN_FILL   = BG_2
ROOM_UNSEEN_STROKE = (60, 58, 80)

# ---------------------------------------------------------------------------
# Typography — font family name strings (must match loaded TTF family names)
# ---------------------------------------------------------------------------

FONT_SERIF       = "IM Fell English"
FONT_SERIF_ITALIC= "IM Fell English"        # use italic=True in draw_text
FONT_SIGIL       = "IM Fell English SC"     # small-caps; decorative glyphs, section dividers
FONT_MONO        = "JetBrains Mono"
FONT_MONO_MED    = "JetBrains Mono"  # DWrite groups Medium under the base family name
FONT_UI          = "Inter"
FONT_UI_MED      = "Inter"       # DWrite groups Medium/Bold under the base family name
FONT_UI_BOLD     = "Inter"       # use bold=True in draw_text for bold weight

# ---------------------------------------------------------------------------
# Font size scale (px)
# ---------------------------------------------------------------------------

TEXT_XS   = 9
TEXT_SM   = 10
TEXT_BASE = 12
TEXT_MD   = 13
TEXT_LG   = 14
TEXT_XL   = 15
TEXT_2XL  = 18
TEXT_3XL  = 19
TEXT_4XL  = 22

# ---------------------------------------------------------------------------
# Spacing & border radii (px)
# ---------------------------------------------------------------------------

PAD_XS  = 4
PAD_SM  = 8
PAD_MD  = 12
PAD_LG  = 14
PAD_XL  = 18

RADIUS_SM  = 4
RADIUS_MD  = 6
RADIUS_LG  = 8
RADIUS_XL  = 10
RADIUS_2XL = 14

# ---------------------------------------------------------------------------
# Panel and chrome dimensions (px)
# ---------------------------------------------------------------------------

PANEL_TREE_WIDTH       = 240   # Design Mode left panel
PANEL_INSPECTOR_WIDTH  = 320   # Design Mode right panel
PANEL_CHAT_WIDTH       = 440   # Play Mode left panel
PANEL_STEPPER_WIDTH    = 70    # Play Mode right rail

CHROME_MENUBAR_HEIGHT  = 26    # top of window
CHROME_TITLEBAR_HEIGHT = 44    # below menu bar
# Combined offset views must apply from the top of the window:
CHROME_TOTAL_HEIGHT    = CHROME_MENUBAR_HEIGHT + CHROME_TITLEBAR_HEIGHT  # 70

# ---------------------------------------------------------------------------
# Drawing utility helpers
# ---------------------------------------------------------------------------

def draw_rounded_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    color: tuple,
    border_color: tuple | None = None,
    border_width: float = 1,
) -> None:
    """
    Draw a filled rounded rectangle centred at (x, y).

    Arcade has no native rounded-rect primitive. This implementation uses
    arcade.draw_rect_filled for the body and approximates rounded corners
    with arcade.draw_circle_filled at each corner, then masks the straight
    edges. For a crisper result, replace with a ShapeElementList + cached
    geometry (see spec/VISUAL_DESIGN.md for the recommended approach).
    """
    # Filled body (slightly inset to leave room for corner circles)
    arcade.draw_rect_filled(
        arcade.XYWH(x, y, width, height), color
    )
    # Corner circles to approximate rounding
    half_w = width / 2 - radius
    half_h = height / 2 - radius
    for cx, cy in [
        (x - half_w, y - half_h),
        (x + half_w, y - half_h),
        (x - half_w, y + half_h),
        (x + half_w, y + half_h),
    ]:
        arcade.draw_circle_filled(cx, cy, radius, color)

    if border_color:
        arcade.draw_rect_outline(
            arcade.XYWH(x, y, width, height), border_color, border_width
        )


def draw_kicker(
    text: str,
    x: float,
    y: float,
    anchor_x: str = "left",
) -> None:
    """Draw a small uppercase mono label (section kicker)."""
    if anchor_x == "left":
        arcade.draw_rect_filled(arcade.XYWH(x - 6, y, 2, 14), TEAL)
    arcade.draw_text(
        text.upper(),
        x, y,
        INK_2,
        font_size=TEXT_SM,
        font_name=FONT_MONO,
        anchor_x=anchor_x,
    )


def draw_chip(
    text: str,
    cx: float,
    cy: float,
    color: str = "default",
    width: int = 80,
) -> None:
    """Draw a small rounded pill label."""
    palette = {
        "default": (BG_3, INK_2),
        "teal":    (TEAL_DIM, TEAL),
        "violet":  (VIOLET_DIM, VIOLET),
        "ember":   ((72, 38, 20), EMBER),
        "gold":    ((90, 78, 22), GOLD),
    }
    bg, fg = palette.get(color, palette["default"])
    draw_rounded_rect(cx, cy, width, 20, RADIUS_SM, bg)
    arcade.draw_text(
        text, cx, cy, fg,
        font_size=TEXT_SM,
        font_name=FONT_MONO,
        anchor_x="center",
        anchor_y="center",
    )
