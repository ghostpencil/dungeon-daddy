"""Tests for dungeon_daddy/ui/theme.py — written before implementation."""

# ---------------------------------------------------------------------------
# Behavior 1: All named color constants are valid RGB/RGBA tuples (0–255)
# ---------------------------------------------------------------------------

EXPECTED_COLORS = [
    "BG_0", "BG_1", "BG_2", "BG_3", "BG_HI",
    "LINE_DIM", "LINE", "LINE_HI",
    "INK_1", "INK_2", "INK_3", "INK_4",
    "TEAL", "TEAL_DIM", "TEAL_GLOW",
    "VIOLET", "VIOLET_DIM", "VIOLET_GLOW",
    "EMBER", "EMBER_GLOW",
    "GOLD",
    "PATH_A_COLOR", "PATH_B_COLOR", "PATH_BOTH",
]


def test_all_color_tuples_are_valid_rgb():
    import dungeon_daddy.ui.theme as theme
    for name in EXPECTED_COLORS:
        value = getattr(theme, name)
        assert isinstance(value, tuple), f"{name} must be a tuple, got {type(value)}"
        assert len(value) in (3, 4), f"{name} must have 3 or 4 channels, got {len(value)}"
        for i, channel in enumerate(value):
            assert 0 <= channel <= 255, (
                f"{name}[{i}] = {channel} is out of range 0-255"
            )


# ---------------------------------------------------------------------------
# Behavior 2: ROOM_COLORS covers all 7 types with fill + stroke
# ---------------------------------------------------------------------------

REQUIRED_ROOM_TYPES = {"hall", "shrine", "lair", "vault", "stair", "study", "boss"}


def test_room_colors_covers_all_types():
    from dungeon_daddy.ui.theme import ROOM_COLORS
    assert set(ROOM_COLORS.keys()) == REQUIRED_ROOM_TYPES


def test_room_colors_each_has_fill_and_stroke():
    from dungeon_daddy.ui.theme import ROOM_COLORS
    for room_type, colors in ROOM_COLORS.items():
        assert "fill" in colors, f"ROOM_COLORS['{room_type}'] missing 'fill'"
        assert "stroke" in colors, f"ROOM_COLORS['{room_type}'] missing 'stroke'"
        for key in ("fill", "stroke"):
            val = colors[key]
            assert isinstance(val, tuple), (
                f"ROOM_COLORS['{room_type}']['{key}'] must be a tuple"
            )
            assert len(val) in (3, 4)
            assert all(0 <= c <= 255 for c in val)


# ---------------------------------------------------------------------------
# Behavior 3: draw_title_bar calls arcade.draw_rect_filled
# ---------------------------------------------------------------------------

def test_draw_title_bar_calls_rect_filled(mocker):
    mocker.patch("arcade.draw_rect_filled")
    mocker.patch("arcade.draw_rect_outline")
    mocker.patch("arcade.draw_text")
    mocker.patch("arcade.draw_line")
    import dungeon_daddy.ui.chrome as chrome
    class FakeWindow:
        width = 1400
        height = 900
    chrome.draw_title_bar(FakeWindow(), mode="design", on_mode=lambda m: None)
    import arcade
    assert arcade.draw_rect_filled.call_count >= 1
