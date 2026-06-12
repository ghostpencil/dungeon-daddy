"""Unit tests for ChatPanel.on_mouse_press chip click handling and handle_key_press."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import arcade
import pytest

from dungeon_daddy.data.models import ChatMessage
from dungeon_daddy.ui.panels.chat_panel import ChatPanel


@pytest.fixture
def panel():
    return ChatPanel(on_send=MagicMock())


def _with_chip_rects(panel: ChatPanel) -> ChatPanel:
    """Populate chip rects as draw() would — bypasses arcade rendering."""
    panel._chip_rects = [
        (0.0, 4.0, 110.0, 24.0, "Validate level"),
        (118.0, 4.0, 253.0, 24.0, "Add a secret door"),
    ]
    return panel


def test_chip_click_sends_chip_text(panel):
    _with_chip_rects(panel)
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is True
    panel._on_send.assert_called_once_with("Validate level")


def test_chip_click_second_chip(panel):
    _with_chip_rects(panel)
    panel.on_mouse_press(185.0, 14.0)
    panel._on_send.assert_called_once_with("Add a secret door")


def test_chip_miss_returns_false(panel):
    _with_chip_rects(panel)
    result = panel.on_mouse_press(500.0, 14.0)
    assert result is False
    panel._on_send.assert_not_called()


def test_chip_click_ignored_when_busy(panel):
    _with_chip_rects(panel)
    panel._busy = True
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is False
    panel._on_send.assert_not_called()


def test_chip_click_at_edge(panel):
    _with_chip_rects(panel)
    panel.on_mouse_press(0.0, 4.0)
    panel._on_send.assert_called_once_with("Validate level")


def test_no_chip_rects_returns_false(panel):
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is False


# ---------------------------------------------------------------------------
# handle_key_press — F-12 keyboard shortcuts
# ---------------------------------------------------------------------------

def _with_input(panel: ChatPanel, text: str = "Hello") -> MagicMock:
    """Attach a fake input widget so handle_key_press can read/clear text."""
    fake = MagicMock()
    fake.text = text
    panel._input = fake
    return fake


def test_ctrl_enter_sends_message(panel):
    inp = _with_input(panel, "Hello world")
    result = panel.handle_key_press(arcade.key.ENTER, arcade.key.MOD_CTRL)
    assert result is True
    panel._on_send.assert_called_once_with("Hello world")
    assert inp.text == ""


def test_ctrl_enter_whitespace_no_send(panel):
    _with_input(panel, "   ")
    result = panel.handle_key_press(arcade.key.ENTER, arcade.key.MOD_CTRL)
    assert result is True
    panel._on_send.assert_not_called()


def test_ctrl_enter_when_busy_no_send(panel):
    _with_input(panel, "Hello")
    panel._busy = True
    result = panel.handle_key_press(arcade.key.ENTER, arcade.key.MOD_CTRL)
    assert result is True
    panel._on_send.assert_not_called()


def test_plain_enter_not_consumed(panel):
    _with_input(panel, "Hello")
    result = panel.handle_key_press(arcade.key.ENTER, 0)
    assert result is False
    panel._on_send.assert_not_called()


def test_other_key_not_consumed(panel):
    _with_input(panel, "Hello")
    result = panel.handle_key_press(arcade.key.Z, arcade.key.MOD_CTRL)
    assert result is False
    panel._on_send.assert_not_called()


# ---------------------------------------------------------------------------
# CE-5 — context_loaded chip state
# ---------------------------------------------------------------------------


def test_set_context_loaded_true(panel):
    panel.set_context_loaded(True)
    assert panel._context_loaded is True


def test_set_context_loaded_false_clears(panel):
    panel.set_context_loaded(True)
    panel.set_context_loaded(False)
    assert panel._context_loaded is False


# ---------------------------------------------------------------------------
# MC-1 Step 4 — label cache
# ---------------------------------------------------------------------------

def _mock_pyglet_html_label():
    mock_inner = MagicMock()
    mock_inner.content_height = 50
    return mock_inner


def test_label_cache_starts_empty(panel):
    assert panel._label_cache == {}


def test_get_or_build_label_creates_on_miss(panel):
    msg = ChatMessage(role="dm", content="hello")
    with patch("pyglet.text.HTMLLabel", return_value=_mock_pyglet_html_label()):
        label = panel._get_or_build_label(0, msg, 300.0)
    assert label is not None
    assert 0 in panel._label_cache


def test_get_or_build_label_returns_same_on_hit(panel):
    msg = ChatMessage(role="dm", content="hello")
    mock_inner = _mock_pyglet_html_label()
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        label1 = panel._get_or_build_label(0, msg, 300.0)
        label2 = panel._get_or_build_label(0, msg, 300.0)
    assert label1 is label2


def test_resize_clears_label_cache(panel):
    msg = ChatMessage(role="dm", content="hello")
    with patch("pyglet.text.HTMLLabel", return_value=_mock_pyglet_html_label()):
        panel._get_or_build_label(0, msg, 300.0)
    assert 0 in panel._label_cache
    panel.resize(0.0, 0.0, 400.0, 600.0)
    assert panel._label_cache == {}


def test_teardown_clears_label_cache(panel):
    msg = ChatMessage(role="dm", content="hello")
    with patch("pyglet.text.HTMLLabel", return_value=_mock_pyglet_html_label()):
        panel._get_or_build_label(0, msg, 300.0)
    assert 0 in panel._label_cache
    panel.teardown(MagicMock())
    assert panel._label_cache == {}


# ---------------------------------------------------------------------------
# MC-1 Step 5 — _bubble_height uses label content_height
# ---------------------------------------------------------------------------


def test_bubble_height_uses_label_content_height(panel):
    msg = ChatMessage(role="dm", content="hello")
    mock_inner = _mock_pyglet_html_label()
    mock_inner.content_height = 80
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        h = panel._bubble_height(0, msg, 300.0)
    assert h == 116  # max(40, 80 + 8*2 + 20)


def test_bubble_height_clamps_to_minimum_40(panel):
    msg = ChatMessage(role="dm", content="")
    mock_inner = _mock_pyglet_html_label()
    mock_inner.content_height = 0
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        h = panel._bubble_height(0, msg, 300.0)
    assert h == 40


def test_compute_heights_uses_label_content_height(panel):
    panel._messages = [
        ChatMessage(role="dm", content="hello"),
        ChatMessage(role="gm", content="world"),
    ]
    mock_inner = _mock_pyglet_html_label()
    mock_inner.content_height = 60
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        heights = panel._compute_heights(300.0)
    assert len(heights) == 2
    assert all(h == 96 for h in heights)  # max(40, 60 + 16 + 20)


# ---------------------------------------------------------------------------
# MC-1 Step 6 — _draw_messages_inner uses label.draw()
# ---------------------------------------------------------------------------


def test_draw_messages_inner_calls_label_draw(panel):
    msg = ChatMessage(role="dm", content="hello")
    panel._messages = [msg]
    mock_label = MagicMock()
    panel._label_cache[0] = mock_label
    with patch("dungeon_daddy.ui.panels.chat_panel.arcade"):
        panel._draw_messages_inner(
            bx=10.0, y_bot=0.0, y_top=600.0,
            bubble_w=300.0, pad=8.0,
            heights=[80], n=1, off=0.0,
        )
    mock_label.update_position.assert_called_once()
    mock_label.draw.assert_called_once()


# ---------------------------------------------------------------------------
# 39.S1 — set_pending_chips and set_chip_click_callback
# ---------------------------------------------------------------------------


def test_set_pending_chips_stores_labels(panel):
    panel.set_pending_chips(["STUDY", "SENSE", "No Roll"])
    assert panel._pending_chips == ["STUDY", "SENSE", "No Roll"]


def test_set_pending_chips_none_clears(panel):
    panel.set_pending_chips(["STUDY"])
    panel.set_pending_chips(None)
    assert panel._pending_chips is None


def test_pending_chips_none_by_default(panel):
    assert panel._pending_chips is None


def test_set_chip_click_callback_stores_fn(panel):
    cb = MagicMock()
    panel.set_chip_click_callback(cb)
    assert panel._on_chip_click is cb


def test_chip_click_callback_none_by_default(panel):
    assert panel._on_chip_click is None


def test_pending_chip_click_calls_callback_not_send(panel):
    cb = MagicMock()
    panel.set_pending_chips(["STUDY", "SENSE", "No Roll"])
    panel.set_chip_click_callback(cb)
    panel._chip_rects = [(0.0, 4.0, 80.0, 24.0, "STUDY")]
    result = panel.on_mouse_press(40.0, 14.0)
    assert result is True
    cb.assert_called_once_with("STUDY")
    panel._on_send.assert_not_called()


def test_pending_chip_click_no_callback_consumes_click(panel):
    """Click on pending chip with no callback set: consumed but nothing called."""
    panel.set_pending_chips(["STUDY"])
    panel._chip_rects = [(0.0, 4.0, 80.0, 24.0, "STUDY")]
    result = panel.on_mouse_press(40.0, 14.0)
    assert result is True
    panel._on_send.assert_not_called()


def test_static_chip_click_calls_on_send_when_no_pending(panel):
    """Without pending chips, existing _on_send routing still works."""
    panel._chip_rects = [(0.0, 4.0, 110.0, 24.0, "Describe room")]
    result = panel.on_mouse_press(55.0, 14.0)
    assert result is True
    panel._on_send.assert_called_once_with("Describe room")


# ---------------------------------------------------------------------------
# 39.S4 — set_actor_mini_card
# ---------------------------------------------------------------------------

def test_actor_mini_card_initially_none(panel):
    assert panel._actor_mini_card is None


def test_set_actor_mini_card_stores_card(panel):
    from dungeon_daddy.ui.actor_mini_card import ActorMiniCardData
    card = ActorMiniCardData(actor_name="Mara")
    panel.set_actor_mini_card(card)
    assert panel._actor_mini_card is card


def test_set_actor_mini_card_none_clears(panel):
    from dungeon_daddy.ui.actor_mini_card import ActorMiniCardData
    panel.set_actor_mini_card(ActorMiniCardData(actor_name="Mara"))
    panel.set_actor_mini_card(None)
    assert panel._actor_mini_card is None


# ---------------------------------------------------------------------------
# 39.S6.2 — Actor switcher: set_has_multiple_actors / set_actor_switch_callback
# ---------------------------------------------------------------------------

def test_has_multiple_actors_false_by_default(panel):
    assert panel._has_multiple_actors is False


def test_set_has_multiple_actors_true(panel):
    panel.set_has_multiple_actors(True)
    assert panel._has_multiple_actors is True


def test_set_has_multiple_actors_false(panel):
    panel.set_has_multiple_actors(True)
    panel.set_has_multiple_actors(False)
    assert panel._has_multiple_actors is False


def test_actor_switch_callback_none_by_default(panel):
    assert panel._actor_switch_callback is None


def test_set_actor_switch_callback_stores_fn(panel):
    cb = MagicMock()
    panel.set_actor_switch_callback(cb)
    assert panel._actor_switch_callback is cb


def test_mini_card_prev_rect_none_by_default(panel):
    assert panel._mini_card_prev_rect is None


def test_mini_card_next_rect_none_by_default(panel):
    assert panel._mini_card_next_rect is None


def test_prev_arrow_click_calls_switch_callback(panel):
    cb = MagicMock()
    panel.set_actor_switch_callback(cb)
    panel._mini_card_prev_rect = (0.0, 98.0, 15.0, 112.0)
    result = panel.on_mouse_press(7.5, 105.0)
    assert result is True
    cb.assert_called_once_with("prev")


def test_next_arrow_click_calls_switch_callback(panel):
    cb = MagicMock()
    panel.set_actor_switch_callback(cb)
    panel._mini_card_next_rect = (200.0, 98.0, 215.0, 112.0)
    result = panel.on_mouse_press(207.5, 105.0)
    assert result is True
    cb.assert_called_once_with("next")


def test_arrow_click_no_callback_returns_true(panel):
    panel._mini_card_prev_rect = (0.0, 98.0, 15.0, 112.0)
    result = panel.on_mouse_press(7.5, 105.0)
    assert result is True
    panel._on_send.assert_not_called()


def test_arrow_miss_returns_false(panel):
    panel._mini_card_prev_rect = (0.0, 98.0, 15.0, 112.0)
    panel._mini_card_next_rect = (200.0, 98.0, 215.0, 112.0)
    result = panel.on_mouse_press(100.0, 105.0)
    assert result is False


# ---------------------------------------------------------------------------
# 39.S6.3 — In-chat action card: add_action_card / resolve_active_card
# ---------------------------------------------------------------------------

def test_add_action_card_stores_card_data(panel):
    panel.add_action_card("Talvas", "I study the runes", ["STUDY", "SENSE"])
    assert len(panel._action_cards) == 1
    idx = next(iter(panel._action_cards))
    card = panel._action_cards[idx]
    assert card.actor_name == "Talvas"
    assert "study the runes" in card.intent_text
    assert card.action_keys == ["STUDY", "SENSE"]
    assert card.resolved_label is None


def test_add_action_card_sets_active_card_index(panel):
    panel.add_action_card("Talvas", "I study the runes", ["STUDY", "SENSE"])
    assert panel._active_card_index is not None


def test_add_action_card_deactivates_previous_card(panel):
    panel.add_action_card("Talvas", "first intent", ["STUDY"])
    first_idx = panel._active_card_index
    panel.add_action_card("Talvas", "second intent", ["SENSE"])
    second_idx = panel._active_card_index
    assert second_idx != first_idx
    # Previous card still stored but no longer active
    assert first_idx in panel._action_cards
    assert panel._active_card_index == second_idx


def test_active_card_index_none_by_default(panel):
    assert panel._active_card_index is None


def test_action_cards_empty_by_default(panel):
    assert panel._action_cards == {}


def test_resolve_active_card_sets_resolved_label(panel):
    panel.add_action_card("Talvas", "I study the runes", ["STUDY", "SENSE"])
    panel.resolve_active_card("STUDY")
    idx = panel._active_card_index
    assert panel._action_cards[idx].resolved_label == "STUDY"


def test_resolve_active_card_no_op_when_no_active_card(panel):
    panel.resolve_active_card("STUDY")  # should not raise


def test_action_card_button_rects_empty_by_default(panel):
    assert panel._active_card_button_rects == []


def test_active_card_button_click_fires_chip_click_callback(panel):
    cb = MagicMock()
    panel.set_chip_click_callback(cb)
    panel.add_action_card("Talvas", "I study the runes", ["STUDY", "SENSE"])
    # Manually set a button rect as draw() would
    panel._active_card_button_rects = [
        ("STUDY", (10.0, 50.0, 70.0, 70.0)),
        ("SENSE", (80.0, 50.0, 140.0, 70.0)),
    ]
    result = panel.on_mouse_press(40.0, 60.0)
    assert result is True
    cb.assert_called_once_with("STUDY")


def test_resolved_card_does_not_fire_callback(panel):
    cb = MagicMock()
    panel.set_chip_click_callback(cb)
    panel.add_action_card("Talvas", "I study the runes", ["STUDY", "SENSE"])
    panel.resolve_active_card("STUDY")
    panel._active_card_button_rects = [
        ("STUDY", (10.0, 50.0, 70.0, 70.0)),
    ]
    panel.on_mouse_press(40.0, 60.0)
    cb.assert_not_called()


def test_card_button_miss_falls_through(panel):
    cb = MagicMock()
    panel.set_chip_click_callback(cb)
    panel.add_action_card("Talvas", "I study the runes", ["STUDY"])
    panel._active_card_button_rects = [("STUDY", (10.0, 50.0, 70.0, 70.0))]
    result = panel.on_mouse_press(200.0, 60.0)
    assert result is False
    cb.assert_not_called()


# ---------------------------------------------------------------------------
# 39.S6 UI fix — hover tracking on action card buttons
# ---------------------------------------------------------------------------

def test_hovered_card_button_none_by_default(panel):
    assert panel._hovered_card_button is None


def test_on_mouse_motion_sets_hovered_button(panel):
    panel.add_action_card("Talvas", "I study the runes", ["STUDY", "SENSE"])
    panel._active_card_button_rects = [
        ("STUDY", (10.0, 50.0, 60.0, 18.0)),
        ("SENSE", (80.0, 50.0, 60.0, 18.0)),
    ]
    panel.on_mouse_motion(40.0, 59.0)
    assert panel._hovered_card_button == "STUDY"


def test_on_mouse_motion_clears_hovered_when_outside(panel):
    panel.add_action_card("Talvas", "I study the runes", ["STUDY"])
    panel._active_card_button_rects = [("STUDY", (10.0, 50.0, 60.0, 18.0))]
    panel._hovered_card_button = "STUDY"
    panel.on_mouse_motion(200.0, 59.0)
    assert panel._hovered_card_button is None


def test_on_mouse_motion_no_hover_when_card_resolved(panel):
    panel.add_action_card("Talvas", "I study the runes", ["STUDY"])
    panel.resolve_active_card("STUDY")
    panel._active_card_button_rects = [("STUDY", (10.0, 50.0, 60.0, 18.0))]
    panel.on_mouse_motion(40.0, 59.0)
    assert panel._hovered_card_button is None


def test_on_mouse_motion_no_hover_when_no_active_card(panel):
    panel.on_mouse_motion(40.0, 59.0)
    assert panel._hovered_card_button is None
