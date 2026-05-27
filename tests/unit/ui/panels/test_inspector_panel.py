"""Tests for InspectorPanel saved/session button state."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.ui.panels.inspector_panel import InspectorPanel

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _level() -> Level:
    room = Room(id="r1", num=1, name="Hall", x=0, y=0, w=2, h=2, type="hall", note="")
    return Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=10, height=10, entries=[],
        rooms=[room], connections=[],
    )


def _dungeon_with_levels() -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q"),
        levels=[_level()],
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


# ---------------------------------------------------------------------------
# hit_start_play — saved guard
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# draw() — Start Play / Continue Play label
# ---------------------------------------------------------------------------

def _draw_text_labels(panel: InspectorPanel) -> list[str]:
    """Run draw() with arcade mocked; return all text strings passed to draw_text."""
    with patch("dungeon_daddy.ui.panels.inspector_panel.arcade") as mock_arcade, \
         patch("dungeon_daddy.ui.panels.inspector_panel.draw_kicker"), \
         patch("dungeon_daddy.ui.panels.inspector_panel.draw_chip"), \
         patch("dungeon_daddy.ui.panels.inspector_panel.draw_rounded_rect"):
        mock_arcade.XYWH = MagicMock(return_value=MagicMock())
        panel.draw()
    return [call.args[0] for call in mock_arcade.draw_text.call_args_list]


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


# ---------------------------------------------------------------------------
# on_mouse_press — tab-switch logic
# ---------------------------------------------------------------------------

def _panel_with_tab_rects() -> InspectorPanel:
    """Panel with _tab_rects pre-populated at known coordinates."""
    panel = _make_panel()
    panel._tab_rects = {
        "settings": (0.0, 0.0, 100.0, 32.0),
        "loops":    (100.0, 0.0, 200.0, 32.0),
    }
    return panel


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

    panel.on_mouse_press(50.0, 99.0)  # below tab rects

    assert panel._active_tab == "settings"


def test_loops_tab_delegates_to_loops_panel():
    """Clicks inside the loops content area are forwarded to _loops_panel."""
    panel = _panel_with_tab_rects()
    panel._active_tab = "loops"
    panel._loops_panel.on_mouse_press.return_value = True

    # Click outside tab rects so tab-switch branch is skipped
    panel.on_mouse_press(50.0, 99.0)

    panel._loops_panel.on_mouse_press.assert_called_once_with(50.0, 99.0, 0)
