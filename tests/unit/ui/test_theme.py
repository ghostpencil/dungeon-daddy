"""Tests for dungeon_daddy/ui/theme.py — written before implementation."""
import inspect
import pytest


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


def test_all_color_constants_exist():
    import dungeon_daddy.ui.theme as theme
    for name in EXPECTED_COLORS:
        assert hasattr(theme, name), f"Missing color constant: {name}"


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


def test_all_module_level_tuples_are_valid_colors():
    """Broader check: every tuple exported from theme is a valid color."""
    import dungeon_daddy.ui.theme as theme
    for name, value in inspect.getmembers(theme):
        if name.startswith("_"):
            continue
        if isinstance(value, tuple) and len(value) in (3, 4):
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
        # Both must be valid color tuples
        for key in ("fill", "stroke"):
            val = colors[key]
            assert isinstance(val, tuple), (
                f"ROOM_COLORS['{room_type}']['{key}'] must be a tuple"
            )
            assert len(val) in (3, 4)
            assert all(0 <= c <= 255 for c in val)


# ---------------------------------------------------------------------------
# Behavior 3: Font name constants are non-empty strings
# ---------------------------------------------------------------------------

EXPECTED_FONTS = [
    "FONT_SERIF", "FONT_SERIF_ITALIC", "FONT_SIGIL",
    "FONT_MONO", "FONT_MONO_MED",
    "FONT_UI", "FONT_UI_MED", "FONT_UI_BOLD",
]


def test_all_font_constants_exist():
    import dungeon_daddy.ui.theme as theme
    for name in EXPECTED_FONTS:
        assert hasattr(theme, name), f"Missing font constant: {name}"


def test_all_font_constants_are_nonempty_strings():
    import dungeon_daddy.ui.theme as theme
    for name in EXPECTED_FONTS:
        value = getattr(theme, name)
        assert isinstance(value, str), f"{name} must be a str, got {type(value)}"
        assert len(value) > 0, f"{name} must not be empty"


# ---------------------------------------------------------------------------
# Behavior 4: Panel width and chrome height constants are positive integers
# ---------------------------------------------------------------------------

EXPECTED_DIMENSIONS = [
    "PANEL_TREE_WIDTH",
    "PANEL_INSPECTOR_WIDTH",
    "PANEL_CHAT_WIDTH",
    "PANEL_STEPPER_WIDTH",
    "CHROME_MENUBAR_HEIGHT",
    "CHROME_TITLEBAR_HEIGHT",
]


def test_dimension_constants_exist():
    import dungeon_daddy.ui.theme as theme
    for name in EXPECTED_DIMENSIONS:
        assert hasattr(theme, name), f"Missing dimension constant: {name}"


def test_dimension_constants_are_positive_integers():
    import dungeon_daddy.ui.theme as theme
    for name in EXPECTED_DIMENSIONS:
        value = getattr(theme, name)
        assert isinstance(value, int), f"{name} must be an int, got {type(value)}"
        assert value > 0, f"{name} must be positive, got {value}"


def test_chrome_heights_sum_to_70():
    from dungeon_daddy.ui.theme import CHROME_MENUBAR_HEIGHT, CHROME_TITLEBAR_HEIGHT
    assert CHROME_MENUBAR_HEIGHT + CHROME_TITLEBAR_HEIGHT == 70


# ---------------------------------------------------------------------------
# Behavior 5: Drawing utilities are importable callables
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Behavior 6: MenuAction dataclass has correct fields and defaults
# ---------------------------------------------------------------------------

def test_menu_action_fields():
    from dungeon_daddy.ui.chrome import MenuAction
    action = MenuAction(label="Save", handler=lambda: None)
    assert action.label == "Save"
    assert action.enabled is True
    assert action.implemented is True
    assert callable(action.handler)


def test_menu_action_not_implemented_default():
    from dungeon_daddy.ui.chrome import MenuAction
    action = MenuAction(label="Undo", handler=lambda: None, implemented=False)
    assert action.implemented is False
    assert action.enabled is True


def test_menu_action_disabled():
    from dungeon_daddy.ui.chrome import MenuAction
    action = MenuAction(label="Save", handler=lambda: None, enabled=False)
    assert action.enabled is False


# ---------------------------------------------------------------------------
# Behavior 7: MenuAction with implemented=False still has a callable handler
# ---------------------------------------------------------------------------

def test_nyi_handler_is_callable():
    from dungeon_daddy.ui.chrome import MenuAction
    nyi_calls = []
    def nyi(): nyi_calls.append(1)
    action = MenuAction(label="Undo", handler=nyi, implemented=False)
    action.handler()
    assert nyi_calls == [1]


# ---------------------------------------------------------------------------
# Behavior 8: draw_menu_bar and draw_title_bar call arcade.draw_rect_filled
# ---------------------------------------------------------------------------

def test_draw_menu_bar_calls_rect_filled(mocker):
    mocker.patch("arcade.draw_rect_filled")
    mocker.patch("arcade.draw_text")
    mocker.patch("arcade.draw_line")
    import dungeon_daddy.ui.chrome as chrome
    # Minimal fake window
    class FakeWindow:
        width = 1400
        height = 900
    chrome.draw_menu_bar(FakeWindow())
    import arcade
    assert arcade.draw_rect_filled.call_count >= 1


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
