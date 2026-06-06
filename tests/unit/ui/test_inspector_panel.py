"""Unit tests for InspectorPanel F-13 — editable Settings fields."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meta(**kw) -> DungeonMeta:
    defaults = dict(
        title="Test Dungeon",
        theme="Cursed Tomb",
        setting="A crypt.",
        party="4 adventurers",
        quest="Find the relic.",
    )
    defaults.update(kw)
    return DungeonMeta(**defaults)


def _dungeon(**meta_kw) -> Dungeon:
    return Dungeon(meta=_meta(**meta_kw), levels=[])


def _panel():
    from dungeon_daddy.ui.panels.inspector_panel import InspectorPanel
    return InspectorPanel()


# ---------------------------------------------------------------------------
# Behavior 1 — DungeonMeta new fields have correct defaults
# ---------------------------------------------------------------------------

def test_dungeon_meta_party_size_default():
    meta = _meta()
    assert meta.party_size == 0


def test_dungeon_meta_party_level_default():
    meta = _meta()
    assert meta.party_level == 0


def test_dungeon_meta_num_levels_default():
    meta = _meta()
    assert meta.num_levels == 3


def test_dungeon_meta_complexity_default():
    meta = _meta()
    assert meta.complexity == "Moderate"


# ---------------------------------------------------------------------------
# Behavior 2 — set_on_settings_change registers callback
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Behaviors 3–6 — on_settings_field_change updates meta and fires callback
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field,raw,expected", [
    ("theme", "dark forest", "dark forest"),
    ("party_size", "5", 5),
    ("party_level", "4", 4),
    ("num_levels", "4", 4),
])
def test_on_settings_field_change_updates_meta(field, raw, expected):
    panel = _panel()
    dungeon = _dungeon()
    panel.set_dungeon(dungeon)
    panel.on_settings_field_change(field, raw)
    assert getattr(dungeon.meta, field) == expected


@pytest.mark.parametrize("field,raw", [
    ("theme", "dark forest"),
    ("party_size", "5"),
    ("party_level", "4"),
    ("num_levels", "4"),
])
def test_on_settings_field_change_fires_callback(field, raw):
    panel = _panel()
    cb = MagicMock()
    panel.set_on_settings_change(cb)
    dungeon = _dungeon()
    panel.set_dungeon(dungeon)
    panel.on_settings_field_change(field, raw)
    cb.assert_called_once_with(dungeon.meta)


# ---------------------------------------------------------------------------
# Behavior 7 — on_complexity_change updates meta and fires callback
# ---------------------------------------------------------------------------

def test_on_complexity_change_updates_meta():
    panel = _panel()
    dungeon = _dungeon()
    panel.set_dungeon(dungeon)
    panel.on_complexity_change("Deep")
    assert dungeon.meta.complexity == "Deep"


def test_on_complexity_change_fires_callback():
    panel = _panel()
    cb = MagicMock()
    panel.set_on_settings_change(cb)
    dungeon = _dungeon()
    panel.set_dungeon(dungeon)
    panel.on_complexity_change("Deep")
    cb.assert_called_once_with(dungeon.meta)


# ---------------------------------------------------------------------------
# Behavior 8 — on_mouse_press on complexity segment calls on_complexity_change
# ---------------------------------------------------------------------------

def test_complexity_segment_click_fires_change():
    panel = _panel()
    dungeon = _dungeon()
    panel.set_dungeon(dungeon)
    # Seed rects as draw() would — (left, bottom, right, top, label)
    panel._complexity_seg_rects = [
        (10.0, 0.0, 60.0, 24.0, "Light"),
        (60.0, 0.0, 120.0, 24.0, "Moderate"),
        (120.0, 0.0, 180.0, 24.0, "Deep"),
    ]
    panel.on_mouse_press(140.0, 12.0)
    assert dungeon.meta.complexity == "Deep"


def test_complexity_segment_click_returns_true():
    panel = _panel()
    dungeon = _dungeon()
    panel.set_dungeon(dungeon)
    panel._complexity_seg_rects = [
        (10.0, 0.0, 60.0, 24.0, "Light"),
    ]
    result = panel.on_mouse_press(35.0, 12.0)
    assert result is True


# ---------------------------------------------------------------------------
# Behavior 9 — no dungeon loaded → on_settings_field_change is a no-op
# ---------------------------------------------------------------------------

def test_on_settings_field_change_no_dungeon_no_crash():
    panel = _panel()
    cb = MagicMock()
    panel.set_on_settings_change(cb)
    panel.on_settings_field_change("theme", "irrelevant")
    cb.assert_not_called()


def test_on_complexity_change_no_dungeon_no_crash():
    panel = _panel()
    cb = MagicMock()
    panel.set_on_settings_change(cb)
    panel.on_complexity_change("Light")
    cb.assert_not_called()


# ---------------------------------------------------------------------------
# C-3 — Context Docs UI
# ---------------------------------------------------------------------------

from dungeon_daddy.data.models import ContextDocType
from dungeon_daddy.ui.panels.inspector_panel import ContextDocStatus


def _status(label="Setting Doc", doc_type=ContextDocType.SETTING, level_id=None, word_count=None):
    return ContextDocStatus(label=label, doc_type=doc_type, level_id=level_id, word_count=word_count)



def test_context_doc_row_click_fires_callback():
    panel = _panel()
    cb = MagicMock()
    panel.set_on_context_doc_click(cb)
    st = _status("Setting Doc", ContextDocType.SETTING, level_id=None)
    panel._context_doc_rects = [(10.0, 0.0, 200.0, 24.0, st)]
    panel._active_tab = "settings"
    panel.on_mouse_press(100.0, 12.0)
    cb.assert_called_once_with(ContextDocType.SETTING, None)


def test_context_doc_row_click_level_design_passes_level_id():
    panel = _panel()
    cb = MagicMock()
    panel.set_on_context_doc_click(cb)
    st = _status("Level Design", ContextDocType.LEVEL_DESIGN, level_id=2)
    panel._context_doc_rects = [(10.0, 0.0, 200.0, 24.0, st)]
    panel._active_tab = "settings"
    panel.on_mouse_press(100.0, 12.0)
    cb.assert_called_once_with(ContextDocType.LEVEL_DESIGN, 2)


def test_context_doc_row_click_returns_true():
    panel = _panel()
    st = _status()
    panel._context_doc_rects = [(10.0, 0.0, 200.0, 24.0, st)]
    panel._active_tab = "settings"
    result = panel.on_mouse_press(100.0, 12.0)
    assert result is True


# ---------------------------------------------------------------------------
# Theme text area — _wrap_text
# ---------------------------------------------------------------------------

from dungeon_daddy.ui.panels.inspector_panel import InspectorPanel


def test_wrap_text_short_stays_on_one_line():
    lines = InspectorPanel._wrap_text("Hello world", 30)
    assert lines == ["Hello world"]


def test_wrap_text_long_wraps_to_multiple_lines():
    text = "The quick brown fox jumps over the lazy dog"
    lines = InspectorPanel._wrap_text(text, 20)
    assert len(lines) > 1
    assert all(len(line) <= 20 for line in lines)


def test_wrap_text_empty_returns_empty():
    assert InspectorPanel._wrap_text("", 30) == []


def test_wrap_text_preserves_all_words():
    text = "one two three four five"
    lines = InspectorPanel._wrap_text(text, 10)
    assert " ".join(lines) == text


# ---------------------------------------------------------------------------
# Theme text area — on_mouse_scroll
# ---------------------------------------------------------------------------

def test_on_mouse_scroll_inside_area_increments_offset():
    panel = _panel()
    panel._theme_area_rect = (80.0, 100.0, 280.0, 172.0)
    panel._theme_max_scroll = 5
    panel.on_mouse_scroll(150.0, 136.0, -1)  # scroll down
    assert panel._theme_scroll_offset == 1


def test_on_mouse_scroll_up_decrements_offset():
    panel = _panel()
    panel._theme_area_rect = (80.0, 100.0, 280.0, 172.0)
    panel._theme_max_scroll = 5
    panel._theme_scroll_offset = 3
    panel.on_mouse_scroll(150.0, 136.0, 1)  # scroll up
    assert panel._theme_scroll_offset == 2


def test_on_mouse_scroll_clamps_to_zero():
    panel = _panel()
    panel._theme_area_rect = (80.0, 100.0, 280.0, 172.0)
    panel._theme_max_scroll = 5
    panel._theme_scroll_offset = 0
    panel.on_mouse_scroll(150.0, 136.0, 5)  # scroll up when already at top
    assert panel._theme_scroll_offset == 0


def test_on_mouse_scroll_clamps_to_max():
    panel = _panel()
    panel._theme_area_rect = (80.0, 100.0, 280.0, 172.0)
    panel._theme_max_scroll = 3
    panel._theme_scroll_offset = 3
    panel.on_mouse_scroll(150.0, 136.0, -10)  # scroll down past max
    assert panel._theme_scroll_offset == 3


def test_on_mouse_scroll_outside_area_returns_false():
    panel = _panel()
    panel._theme_area_rect = (80.0, 100.0, 280.0, 172.0)
    result = panel.on_mouse_scroll(500.0, 500.0, -1)
    assert result is False


def test_on_mouse_scroll_no_area_rect_returns_false():
    panel = _panel()
    result = panel.on_mouse_scroll(150.0, 136.0, -1)
    assert result is False


# ---------------------------------------------------------------------------
# Pattern Library fallback — empty dungeon.loop_patterns uses bundled catalog
# ---------------------------------------------------------------------------

from unittest.mock import patch

from dungeon_daddy.data.models import LoopPattern, LoopPatternCatalog


def _make_pattern(key: str) -> LoopPattern:
    return LoopPattern(
        key=key, name=key.replace("_", " ").title(),
        blurb="", path_a_length="short", path_b_length="short",
        beats=[], source="test",
    )


def _dungeon_with_level(**meta_kw) -> Dungeon:
    """Dungeon with one stub level so set_dungeon enters the patterns branch."""
    lvl = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        width=10, height=10, entries=[], rooms=[], connections=[],
    )
    return Dungeon(meta=_meta(**meta_kw), levels=[lvl])


def test_set_dungeon_with_empty_loop_patterns_uses_bundled_catalog():
    panel = _panel()
    dungeon = _dungeon_with_level()
    assert dungeon.loop_patterns == {}

    catalog_patterns = {"lock_key": _make_pattern("lock_key"), "pursuit": _make_pattern("pursuit")}
    fake_catalog = LoopPatternCatalog(patterns=catalog_patterns)

    with patch.object(LoopPatternCatalog, "load_bundled", return_value=fake_catalog):
        panel.set_dungeon(dungeon)

    assert panel._loops_panel._patterns == list(catalog_patterns.values())


def test_set_dungeon_with_populated_loop_patterns_uses_dungeon_patterns():
    panel = _panel()
    pat = _make_pattern("gambit")
    dungeon = _dungeon_with_level()
    dungeon = dungeon.model_copy(update={"loop_patterns": {"gambit": pat}})

    with patch.object(LoopPatternCatalog, "load_bundled") as mock_load:
        panel.set_dungeon(dungeon)

    mock_load.assert_not_called()
    assert panel._loops_panel._patterns == [pat]


# ---------------------------------------------------------------------------
# Saved/session button state and tab switching
# (previously in tests/unit/ui/panels/test_inspector_panel.py)
# ---------------------------------------------------------------------------

def _level_with_room() -> Level:
    room = Room(id="r1", num=1, name="Hall", x=0, y=0, w=2, h=2, type="hall", note="")
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=10, height=10, entries=[],
        rooms=[room], connections=[],
    )


def _dungeon_with_levels() -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q"),
        levels=[_level_with_room()],
    )


def _make_panel(is_saved: bool = False, has_session: bool = False) -> InspectorPanel:
    panel = InspectorPanel.__new__(InspectorPanel)
    panel._dungeon = None
    panel._is_saved = is_saved
    panel._has_session = has_session
    panel._active_tab = "settings"
    panel._x = panel._y = 0.0
    panel._w = panel._h = 200.0
    panel._test_drive_rect = None
    panel._start_play_rect = None
    panel._tab_rects = {}
    panel._loops_panel = MagicMock()
    panel._on_settings_change = None
    panel._complexity_seg_rects = []
    panel._context_doc_statuses = []
    panel._context_doc_rects = []
    panel._on_context_doc_click = None
    panel._theme_scroll_offset = 0
    panel._theme_max_scroll = 0
    panel._theme_area_rect = None
    return panel


def _draw_text_labels(panel: InspectorPanel) -> list[str]:
    with patch("dungeon_daddy.ui.panels.inspector_panel.arcade") as mock_arcade, \
         patch("dungeon_daddy.ui.panels.inspector_panel.draw_kicker"), \
         patch("dungeon_daddy.ui.panels.inspector_panel.draw_chip"), \
         patch("dungeon_daddy.ui.panels.inspector_panel.draw_rounded_rect"):
        mock_arcade.XYWH = MagicMock(return_value=MagicMock())
        panel.draw()
    return [call.args[0] for call in mock_arcade.draw_text.call_args_list]


def _panel_with_tab_rects() -> InspectorPanel:
    panel = _make_panel()
    panel._tab_rects = {
        "settings": (0.0, 0.0, 100.0, 32.0),
        "loops":    (100.0, 0.0, 200.0, 32.0),
    }
    return panel


def test_start_play_disabled_when_not_saved():
    panel = _make_panel(is_saved=False)
    panel._dungeon = _dungeon_with_levels()
    panel._start_play_rect = (0.0, 0.0, 100.0, 30.0)
    assert panel.hit_start_play(50.0, 15.0) is False


def test_start_play_enabled_when_saved():
    panel = _make_panel()
    panel._dungeon = _dungeon_with_levels()
    panel._start_play_rect = (0.0, 0.0, 100.0, 30.0)
    panel.set_saved_state(is_saved=True, has_session=False)
    assert panel.hit_start_play(50.0, 15.0) is True


def test_label_is_continue_play_when_has_session():
    panel = _make_panel(is_saved=True, has_session=True)
    panel._dungeon = _dungeon_with_levels()
    labels = _draw_text_labels(panel)
    assert "Continue Play →" in labels
    assert "Start Play →" not in labels


def test_label_is_start_play_when_no_session():
    panel = _make_panel(is_saved=True, has_session=False)
    panel._dungeon = _dungeon_with_levels()
    labels = _draw_text_labels(panel)
    assert "Start Play →" in labels
    assert "Continue Play →" not in labels


def test_clicking_loops_tab_switches_active_tab():
    panel = _panel_with_tab_rects()
    assert panel._active_tab == "settings"
    panel.on_mouse_press(150.0, 16.0)
    assert panel._active_tab == "loops"


def test_clicking_settings_tab_switches_active_tab():
    panel = _panel_with_tab_rects()
    panel._active_tab = "loops"
    panel.on_mouse_press(50.0, 16.0)
    assert panel._active_tab == "settings"


def test_tab_click_consumes_event():
    panel = _panel_with_tab_rects()
    result = panel.on_mouse_press(150.0, 16.0)
    assert result is True


def test_click_outside_tabs_does_not_switch():
    panel = _panel_with_tab_rects()
    panel._active_tab = "settings"
    panel.on_mouse_press(50.0, 99.0)
    assert panel._active_tab == "settings"


def test_loops_tab_delegates_to_loops_panel():
    panel = _panel_with_tab_rects()
    panel._active_tab = "loops"
    panel._loops_panel.on_mouse_press.return_value = True
    panel.on_mouse_press(50.0, 99.0)
    panel._loops_panel.on_mouse_press.assert_called_once_with(50.0, 99.0, 0)
