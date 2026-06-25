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
# Deterministic preview + adaptive action button (Slice 6)
# ---------------------------------------------------------------------------

def test_button_label_roll_for_contested_action():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_noun("mon-1")
    builder._panel.select_verb("study")  # skill verb → contested
    assert builder.button_label() == "ROLL"


def test_button_label_move_for_deterministic_move():
    builder = _builder(
        exits=[{"exit_id": "ex-1", "label": "North Door", "status": "open"}]
    )
    builder._panel.select_verb("move")  # defaults noun to the only exit
    assert builder.button_label() == "MOVE"


def test_button_label_look_for_look_verb():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_noun("mon-1")
    builder._panel.select_verb("look")  # deterministic, intransitive
    assert builder.button_label() == "LOOK"


def test_button_label_do_for_other_deterministic_verb():
    builder = _builder(
        objects=[
            {
                "object_id": "obj-1",
                "display_name": "Lever",
                "slug": "lever",
                "current_state": "ready",
            }
        ]
    )
    builder._panel.select_verb("activate")  # deterministic, not move/look
    assert builder.button_label() == "DO"


def test_preview_lines_contested_shows_likely_roll_and_memory():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_noun("mon-1")
    builder._panel.select_verb("study")
    lines = builder.preview_lines()
    assert lines[0] == "Likely roll: STUDY"
    assert any(line.startswith("Memory:") for line in lines)


def test_preview_lines_deterministic_shows_no_roll():
    builder = _builder(
        exits=[{"exit_id": "ex-1", "label": "North Door", "status": "open"}]
    )
    builder._panel.select_verb("move")
    assert builder.preview_lines()[0] == "No roll — automatic"


def test_preview_lines_includes_risk_when_threat_present():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_noun("mon-1")
    builder._panel.select_verb("study")
    assert any("Gnoll may stir" in line for line in builder.preview_lines())


def test_preview_lines_empty_without_a_card():
    # A bare panel with no context cannot build a Card → no preview.
    builder = InChatActionBuilder(VnaActionPanel())
    assert builder.preview_lines() == []


# ---------------------------------------------------------------------------
# Noun connector — "Look at the …" reads better than "Look the …"
# ---------------------------------------------------------------------------

def test_look_verb_uses_at_the_noun_connector():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_verb("look")
    assert builder._noun_connector() == "at the"


def test_default_noun_connector_is_the():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_verb("study")
    assert builder._noun_connector() == "the"


# ---------------------------------------------------------------------------
# Empty-slot placeholder (CP-3) — an unset slot reads "needs a choice"
# ---------------------------------------------------------------------------

def test_slot_is_unset_true_for_bare_panel():
    # A panel with no context offers nothing, so the verb slot is unselected.
    builder = InChatActionBuilder(VnaActionPanel())
    assert builder.slot_is_unset("verb") is True


def test_slot_is_unset_false_after_selection():
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    builder._panel.select_verb("study")
    assert builder.slot_is_unset("verb") is False


# ---------------------------------------------------------------------------
# Clause-aware wrap (CP-1) — a connector never separates from its slot
# ---------------------------------------------------------------------------

def test_wrap_packs_groups_greedily_when_room():
    # Plenty of width → everything stays on the first line.
    lines = InChatActionBuilder._wrap_units(
        [40.0, 30.0], avail=1000.0, gap=6.0, glued=[False, False]
    )
    assert lines == [0, 0]


def test_wrap_non_glued_unit_starts_new_line_on_overflow():
    # Two wide non-glued units that cannot share a line wrap normally.
    lines = InChatActionBuilder._wrap_units(
        [100.0, 100.0], avail=120.0, gap=6.0, glued=[False, False]
    )
    assert lines == [0, 1]


def test_wrap_keeps_glued_connector_with_its_slot():
    # Units: "<actor> will" | VERB | "the" | NOUN | ADVERB, NOUN glued to "the".
    # avail fits "...will VERB the" but not the NOUN chip → the connector and its
    # noun wrap to the next line *together* (no orphaned "the").
    widths = [40.0, 30.0, 20.0, 100.0, 40.0]
    glued = [False, False, False, True, False]
    lines = InChatActionBuilder._wrap_units(
        widths, avail=110.0, gap=6.0, glued=glued
    )
    assert lines[2] == lines[3]          # connector and noun share a line
    assert lines[3] == lines[1] + 1      # they moved down together


# ---------------------------------------------------------------------------
# draw() records hit rects consistent with slots() / the action button
# ---------------------------------------------------------------------------

def test_draw_records_slot_and_button_rects(monkeypatch):
    builder = _builder(monsters=[{"actor_id": "mon-1", "display_name": "Gnoll"}])
    with patch("dungeon_daddy.ui.theme.draw_rounded_rect"), \
         patch("arcade.draw_rect_filled"), \
         patch("arcade.draw_line"), \
         patch("arcade.draw_text"):
        builder.draw(0.0, 0.0, 440.0, 200.0)
    assert [r[4] for r in builder._slot_rects] == ["verb", "noun", "adverb"]
    assert builder._button_rect is not None
