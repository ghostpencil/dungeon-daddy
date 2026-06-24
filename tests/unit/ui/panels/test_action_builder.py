"""Unit tests for the in-chat Action Builder (Phase 50.6 Slice 4).

The builder reuses ``VnaActionPanel``'s Arcade-free logic core verbatim and adds
a custom-drawn command sentence with click-to-open popup slots. These tests
construct a *real* VnaActionPanel (per the mock policy) and drive the builder
through its public interface; drawing is exercised separately via the ui-test
harness.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.ui.panels.action_builder import InChatActionBuilder
from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel


def _room_context(**kw) -> dict:
    ctx = {
        "room_id": "room-1",
        "objects": [],
        "loose_items": [],
        "npcs": [],
        "monsters": [],
        "exits": [],
    }
    ctx.update(kw)
    return ctx


def _actor(**kw) -> dict:
    a = {"actor_id": "actor-1", "display_name": "Elara", "carried_items": []}
    a.update(kw)
    return a


def _panel(**ctx_kw) -> VnaActionPanel:
    panel = VnaActionPanel()
    panel.set_context(
        actor_abilities=[],
        room_context=_room_context(**ctx_kw),
        actor=_actor(),
        playbook_slug="fighter",
        world_flags=[],
    )
    return panel


def _builder(**ctx_kw) -> InChatActionBuilder:
    return InChatActionBuilder(_panel(**ctx_kw))


# ---------------------------------------------------------------------------
# Tracer bullet — slots() reflects the attached panel's current selection
# ---------------------------------------------------------------------------

def test_slots_expose_verb_noun_adverb_in_order():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    kinds = [kind for kind, _label in builder.slots()]
    assert kinds == ["verb", "noun", "adverb"]


def test_transitive_verb_inserts_target_slot():
    panel = VnaActionPanel()
    panel.set_context(
        actor_abilities=[],
        room_context=_room_context(
            objects=[
                {
                    "object_id": "obj-1",
                    "display_name": "Warden Door",
                    "slug": "warden-door",
                    "current_state": "locked",
                }
            ],
        ),
        actor=_actor(
            carried_items=[
                {"item_id": "key-1", "display_name": "Iron Key", "slug": "iron-key"}
            ]
        ),
        playbook_slug="fighter",
        world_flags=[],
    )
    panel.select_verb("use")
    builder = InChatActionBuilder(panel)
    kinds = [kind for kind, _label in builder.slots()]
    assert kinds == ["verb", "noun", "target", "adverb"]


# ---------------------------------------------------------------------------
# Slot interaction — click a slot chip to open its popup
# ---------------------------------------------------------------------------

def test_click_slot_opens_its_popup():
    builder = _builder()
    builder._slot_rects = [(0.0, 0.0, 60.0, 20.0, "verb")]
    result = builder.on_mouse_press(30.0, 10.0)
    assert result is True
    assert builder._open_slot == "verb"


def test_no_popup_open_by_default():
    builder = _builder()
    assert builder._open_slot is None


def test_popup_labels_for_open_verb_slot_match_panel():
    builder = _builder()
    builder._open_slot = "verb"
    assert builder.popup_labels() == builder._panel.verb_labels()


def test_popup_labels_empty_when_closed():
    builder = _builder()
    assert builder.popup_labels() == []


def test_click_popup_row_selects_option_and_closes():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    target_label = builder._panel.verb_labels()[1]
    builder._open_slot = "verb"
    builder._popup_row_rects = [(0.0, 0.0, 80.0, 16.0, target_label)]
    result = builder.on_mouse_press(40.0, 8.0)
    assert result is True
    assert builder._panel.selected_verb_label() == target_label
    assert builder._open_slot is None


def test_click_outside_open_popup_dismisses_it():
    builder = _builder()
    builder._open_slot = "verb"
    builder._popup_row_rects = [(0.0, 0.0, 80.0, 16.0, "Study")]
    result = builder.on_mouse_press(500.0, 500.0)
    assert result is True
    assert builder._open_slot is None


# ---------------------------------------------------------------------------
# Action button — clicking it submits the current card
# ---------------------------------------------------------------------------

def test_click_action_button_submits_valid_card():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    submitted = MagicMock()
    builder._panel.set_submit_callback(submitted)
    builder._button_rect = (0.0, 0.0, 60.0, 24.0)
    result = builder.on_mouse_press(30.0, 12.0)
    assert result is True
    submitted.assert_called_once()
    card = submitted.call_args.args[0]
    assert card.verb is not None
    assert card.noun_id == "mon-1"


# ---------------------------------------------------------------------------
# draw() records hit rects consistent with slots() / the action button
# ---------------------------------------------------------------------------

def test_draw_records_slot_and_button_rects(monkeypatch):
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    with patch("dungeon_daddy.ui.theme.draw_rounded_rect"), \
         patch("dungeon_daddy.ui.theme.draw_kicker"), \
         patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text"):
        builder.draw(0.0, 0.0, 440.0, 200.0)
    assert [r[4] for r in builder._slot_rects] == ["verb", "noun", "adverb"]
    assert builder._button_rect is not None
