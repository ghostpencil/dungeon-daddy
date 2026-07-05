"""Unit tests for CampaignNavPanel, CampaignListPanel, and CampaignEditPanel — Phase 42/43."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.campaign.manifest import FactionManifest, RoomObjectManifest
from dungeon_daddy.ui.panels.campaign_edit_panel import CampaignEditPanel
from dungeon_daddy.ui.panels.campaign_list_panel import CampaignListPanel
from dungeon_daddy.ui.panels.campaign_nav_panel import CampaignNavPanel

# ---------------------------------------------------------------------------
# Helpers — CampaignEditPanel without Arcade
# ---------------------------------------------------------------------------


def _edit_panel() -> CampaignEditPanel:
    """Construct CampaignEditPanel without Arcade initialisation."""
    panel = CampaignEditPanel.__new__(CampaignEditPanel)
    panel._x = 0.0
    panel._y = 0.0
    panel._w = 300.0
    panel._h = 600.0
    panel._manager = MagicMock()
    panel._widgets = []
    panel.mode = "none"
    panel._on_save = None
    panel._on_cancel = None
    panel._inputs = {}
    panel._labels = []
    panel._extra_data = {}
    panel._number_values = {}
    panel._number_label_centers = {}
    panel._choice_values = {}
    panel._choice_options = {}
    panel._choice_label_centers = {}
    return panel


def _call_show_faction(panel: CampaignEditPanel, faction: FactionManifest, *, is_new: bool = False) -> None:
    """Call show_faction() with arcade widget constructors patched out."""
    mock_widget = MagicMock()
    mock_widget.text = ""
    with (
        patch("arcade.gui.UIInputText", return_value=mock_widget),
        patch("arcade.gui.UIFlatButton", return_value=MagicMock()),
    ):
        panel.show_faction(faction, lambda d: None, lambda: None, is_new=is_new)


# ---------------------------------------------------------------------------
# CampaignNavPanel.section_at
# ---------------------------------------------------------------------------
#
# Panel bounds: x=0, y=0, w=220, h=400
# HEADER_H=38, TITLE_AREA_H=56  → top_of_sections = 400-94 = 306
# Section 0 (player_side): top=306, bot=274, centre=290
# Section 1 (monsters):    top=274, bot=242, centre=258
# Section 7 (validation):  top=82,  bot=50,  centre=66

SECTIONS = ["player_side", "monsters", "npcs", "factions", "clocks", "threats", "lore", "validation"]


def _nav_panel() -> CampaignNavPanel:
    p = CampaignNavPanel()
    p.set_bounds(0, 0, 220, 400)
    p.set_sections(SECTIONS)
    return p


def test_section_at_returns_none_when_no_sections():
    p = CampaignNavPanel()
    p.set_bounds(0, 0, 220, 400)
    p.set_sections([])
    assert p.section_at(10, 350) is None


def test_section_at_first_section():
    p = _nav_panel()
    assert p.section_at(110, 290) == "player_side"


def test_section_at_second_section():
    p = _nav_panel()
    assert p.section_at(110, 258) == "monsters"


def test_section_at_last_section():
    p = _nav_panel()
    # Section 7 top=82, bot=50, centre=66
    assert p.section_at(110, 66) == "validation"


def test_section_at_returns_none_outside_panel_x():
    p = _nav_panel()
    assert p.section_at(250, 290) is None


def test_section_at_returns_none_in_header_and_title_area():
    # y=350 is above top_of_sections=306 (in header/title area)
    p = _nav_panel()
    assert p.section_at(110, 350) is None


def test_section_at_returns_none_below_last_section():
    # Section 7 bottom=50; y=40 is below it
    p = _nav_panel()
    assert p.section_at(110, 40) is None


# ---------------------------------------------------------------------------
# CampaignListPanel.item_at
# ---------------------------------------------------------------------------
#
# Panel bounds: x=220, y=0, w=460, h=400
# HEADER_H=38, CARD_H=80, GAP=8
# Item 0 top = 400-38=362, bottom=362-80=282, centre=322
# Item 1 top = 282-8=274,  bottom=274-80=194, centre=234
# Item 2 top = 194-8=186,  bottom=186-80=106, centre=146


def _list_panel(n_items: int = 3) -> CampaignListPanel:
    p = CampaignListPanel()
    p.set_bounds(220, 0, 460, 400)
    p.set_item_count(n_items)
    return p


def test_item_at_returns_none_when_no_items():
    p = _list_panel(0)
    assert p.item_at(400, 350) is None


def test_item_at_first_item():
    p = _list_panel(3)
    assert p.item_at(400, 322) == 0


def test_item_at_second_item():
    p = _list_panel(3)
    assert p.item_at(400, 234) == 1


def test_item_at_returns_none_in_gap():
    # Gap between item 0 and item 1: y in range 274..282
    p = _list_panel(3)
    assert p.item_at(400, 278) is None


def test_item_at_returns_none_outside_panel_x():
    p = _list_panel(3)
    assert p.item_at(100, 322) is None


def test_item_at_scroll_offset_aware():
    p = _list_panel(3)
    # offset=88 shifts cards UP: card 0 scrolls above panel, card 1 occupies top slot
    p.set_scroll_offset(88)
    assert p.item_at(400, 322) == 1
    assert p.item_at(400, 234) == 2


# ---------------------------------------------------------------------------
# CampaignListPanel.delete_zone_at
# ---------------------------------------------------------------------------
#
# DELETE_ZONE_SIZE=16, DELETE_ZONE_MARGIN=8
# Item 0: card right=680, card top=362
#   zone x ∈ [656, 672], y ∈ [338, 354]; centre (664, 346)
# Item 1: card top=274; zone y ∈ [250, 266]; centre (664, 258)

def test_delete_zone_at_first_item():
    p = _list_panel(3)
    assert p.delete_zone_at(664, 346) == 0


def test_delete_zone_at_second_item():
    p = _list_panel(3)
    assert p.delete_zone_at(664, 258) == 1


def test_delete_zone_at_returns_none_outside_zone():
    p = _list_panel(3)
    assert p.delete_zone_at(400, 322) is None


def test_delete_zone_at_scroll_offset_aware():
    p = _list_panel(3)
    # offset=88 shifts cards UP: card 1 top = 362, zone y ∈ [334, 354]
    p.set_scroll_offset(88)
    assert p.delete_zone_at(664, 344) == 1


# ---------------------------------------------------------------------------
# CampaignListPanel.add_btn_at
# ---------------------------------------------------------------------------
#
# Panel: x=220, y=0, w=460, h=400
# _ADD_BTN_W=70, _ADD_BTN_H=22, _ADD_BTN_PAD=8
# right = 220+460=680; cx = 680-8-35=637; cy = 0+400-19=381
# x ∈ [602, 672]; y ∈ [370, 392]

def test_add_btn_at_centre_returns_true():
    p = _list_panel(0)
    assert p.add_btn_at(637, 381) is True


def test_add_btn_at_body_of_panel_returns_false():
    p = _list_panel(3)
    assert p.add_btn_at(400, 322) is False


# ---------------------------------------------------------------------------
# CampaignListPanel.back_btn_at — Phase 47 rooms drill-down back affordance
# ---------------------------------------------------------------------------
#
# Panel: x=220, y=0, w=460, h=400
# Header band: y ∈ [362, 400]; back zone x ∈ [220, 420]


def test_back_btn_at_in_header_left_zone_returns_true():
    p = _list_panel(0)
    assert p.back_btn_at(300, 380) is True


def test_back_btn_at_below_header_returns_false():
    p = _list_panel(0)
    assert p.back_btn_at(300, 200) is False


def test_back_btn_at_in_add_button_area_returns_false():
    p = _list_panel(0)
    assert p.back_btn_at(637, 381) is False


def test_draw_with_breadcrumb_renders_room_name(mocker):
    p = _list_panel(0)
    mocker.patch("arcade.draw_rect_filled")
    mocker.patch("arcade.draw_rect_outline")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_kicker")
    mock_text = mocker.patch("arcade.draw_text")
    p.draw("rooms", [], None, breadcrumb="Entry Hall")
    all_text = [str(c.args[0]) for c in mock_text.call_args_list]
    assert any("Entry Hall" in t for t in all_text)


# ---------------------------------------------------------------------------
# CampaignListPanel — Slice 7: faction card display
# ---------------------------------------------------------------------------


def _faction(reputation: str = "neutral", tier: int = 0, concept: str | None = None) -> FactionManifest:
    return FactionManifest(
        slug="iron-guild",
        display_name="Iron Guild",
        reputation=reputation,  # type: ignore[arg-type]
        tier=tier,
        concept=concept,
    )


def test_draw_card_factions_routes_to_faction_card_not_actor_card(mocker):
    p = _list_panel(1)
    mock_faction_card = mocker.patch.object(p, "_draw_faction_card")
    mock_actor_card = mocker.patch.object(p, "_draw_actor_card")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_rounded_rect")
    mocker.patch("arcade.draw_text")
    faction = _faction()
    p._draw_card("factions", faction, 0, 220, 300, 460, 80, hovered=False)
    mock_faction_card.assert_called_once()
    mock_actor_card.assert_not_called()


def _chip_colors_from(mocker, p: CampaignListPanel, faction: FactionManifest) -> list[str]:
    """Return the color arguments from every draw_chip call during _draw_faction_card."""
    mock_chip = mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_chip")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_rounded_rect")
    mocker.patch("arcade.draw_text")
    p._draw_faction_card(faction, 0, 300, 460, 80, False)
    return [call.args[3] for call in mock_chip.call_args_list]


def test_faction_card_reputation_chip_hostile_uses_ember(mocker):
    p = _list_panel(1)
    colors = _chip_colors_from(mocker, p, _faction("hostile"))
    assert "ember" in colors


def test_faction_card_reputation_chip_warm_uses_teal(mocker):
    p = _list_panel(1)
    colors = _chip_colors_from(mocker, p, _faction("warm"))
    assert "teal" in colors


def test_faction_card_reputation_chip_allied_uses_gold(mocker):
    p = _list_panel(1)
    colors = _chip_colors_from(mocker, p, _faction("allied"))
    assert "gold" in colors


def test_faction_card_has_no_action_ratings_row(mocker):
    p = _list_panel(1)
    mock_draw_text = mocker.patch("arcade.draw_text")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_chip")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_rounded_rect")
    p._draw_faction_card(_faction(), 0, 300, 460, 80, False)
    all_text = [str(call.args[0]) for call in mock_draw_text.call_args_list]
    assert not any("●" in t for t in all_text)


def test_faction_card_renders_tier_label(mocker):
    p = _list_panel(1)
    mock_draw_text = mocker.patch("arcade.draw_text")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_chip")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_rounded_rect")
    p._draw_faction_card(_faction(tier=2), 0, 300, 460, 80, False)
    all_text = [str(call.args[0]) for call in mock_draw_text.call_args_list]
    assert "Influential" in all_text


# ---------------------------------------------------------------------------
# CampaignEditPanel — Slice 6: faction edit form
# ---------------------------------------------------------------------------


def test_show_faction_sets_mode_faction():
    panel = _edit_panel()
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild")
    _call_show_faction(panel, faction)
    assert panel.mode == "faction"


def test_show_faction_new_sets_mode_new_faction():
    panel = _edit_panel()
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild")
    _call_show_faction(panel, faction, is_new=True)
    assert panel.mode == "new_faction"


def test_faction_form_has_text_input_fields():
    panel = _edit_panel()
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild", concept="A guild", goal="Rule all")
    _call_show_faction(panel, faction)
    assert "display_name" in panel._inputs
    assert "slug" in panel._inputs
    assert "concept" in panel._inputs
    assert "goal" in panel._inputs


def test_faction_form_has_reputation_and_tier_pickers():
    panel = _edit_panel()
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild", reputation="warm", tier=2)
    _call_show_faction(panel, faction)
    assert "reputation_idx" in panel._number_values
    assert "tier" in panel._number_values
    assert panel._number_values["reputation_idx"] == 3  # warm is index 3
    assert panel._number_values["tier"] == 2


def test_faction_form_has_no_actor_fields():
    panel = _edit_panel()
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild")
    _call_show_faction(panel, faction)
    assert not any(k.startswith("rating_") for k in panel._inputs)
    assert not any(k.startswith("stress_") for k in panel._inputs)
    assert not any(k.startswith("rating_") for k in panel._number_values)
    assert not any(k.startswith("stress_") for k in panel._number_values)


def test_collect_faction_inputs_converts_reputation_idx_to_tier_name():
    panel = _edit_panel()
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild", reputation="allied", tier=3)
    _call_show_faction(panel, faction)
    data = panel._collect_faction_inputs()
    assert data["reputation"] == "allied"
    assert "reputation_idx" not in data
    assert data["tier"] == "3"


# ---------------------------------------------------------------------------
# CampaignEditPanel — Slice 9: room object form
# ---------------------------------------------------------------------------


def _make_room_object(**kwargs: object) -> RoomObjectManifest:
    defaults: dict = dict(
        slug="locked-chest",
        display_name="Locked Chest",
        room_id="room-01",
        level_id="level-01",
        archetype="container",
        description="A heavy iron chest.",
        initial_state="sealed",
    )
    defaults.update(kwargs)
    return RoomObjectManifest(**defaults)


def _call_show_room_object(
    panel: CampaignEditPanel, obj: RoomObjectManifest, *, is_new: bool = False
) -> None:
    mock_widget = MagicMock()
    mock_widget.text = ""
    with (
        patch("arcade.gui.UIInputText", return_value=mock_widget),
        patch("arcade.gui.UIFlatButton", return_value=MagicMock()),
    ):
        panel.show_room_object(obj, lambda d: None, lambda: None, is_new=is_new)


def test_show_room_object_sets_mode():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object())
    assert panel.mode == "room_object"


def test_show_room_object_new_sets_mode_new_room_object():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(), is_new=True)
    assert panel.mode == "new_room_object"


def test_room_object_form_text_inputs_present():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object())
    for key in ("display_name", "description", "initial_state"):
        assert key in panel._inputs, f"Expected input '{key}' in panel._inputs"


def test_room_object_form_has_no_slug_input():
    # Slug is system-generated from the name, not user-entered.
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object())
    assert "slug" not in panel._inputs


def test_room_object_form_has_archetype_picker():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(archetype="door"))
    assert "archetype" in panel._choice_values
    assert panel._choice_options["archetype"] == [
        "container", "door", "mechanism", "structure", "trap", "lore_fixture", "resource",
    ]
    assert panel._choice_values["archetype"] == 1  # door is index 1


def test_collect_room_object_inputs_uses_selected_archetype():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(archetype="container"))
    panel._choice_values["archetype"] = 2  # mechanism
    data = panel._collect_inputs()
    assert data["archetype"] == "mechanism"
    assert any(r["trigger"] == "activate" for r in data["transitions"])


def test_collect_room_object_inputs_generates_slug_for_new():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(slug="", display_name=""), is_new=True)
    panel._inputs["display_name"].text = "Cargo Crate"
    data = panel._collect_inputs()
    assert data["slug"] == "cargo-crate"


def test_collect_room_object_inputs_preserves_slug_for_edit():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(slug="locked-chest", display_name="Locked Chest"))
    panel._inputs["display_name"].text = "Totally Renamed"
    data = panel._collect_inputs()
    assert data["slug"] == "locked-chest"


def test_room_object_form_archetype_in_extra_data():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(archetype="door"))
    assert panel._extra_data.get("archetype") == "door"


def test_room_object_form_room_and_level_in_extra_data():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(room_id="room-42", level_id="level-02"))
    assert panel._extra_data.get("room_id") == "room-42"
    assert panel._extra_data.get("level_id") == "level-02"


def test_collect_room_object_inputs_returns_archetype_room_transitions():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(archetype="mechanism", room_id="room-01"))
    data = panel._collect_inputs()
    assert data["archetype"] == "mechanism"
    assert data["room_id"] == "room-01"
    assert "transitions" in data


def test_room_object_form_default_transitions_populated_for_container():
    panel = _edit_panel()
    _call_show_room_object(panel, _make_room_object(archetype="container"))
    transitions = panel._extra_data.get("transitions", [])
    assert len(transitions) > 0


# ---------------------------------------------------------------------------
# default_transitions_for_archetype helper
# ---------------------------------------------------------------------------


def test_default_transitions_container_has_sealed_to_opened():
    from dungeon_daddy.ui.panels.campaign_edit_panel import default_transitions_for_archetype
    t = default_transitions_for_archetype("container")
    assert any(r["from_state"] == "sealed" and r["to_state"] == "opened" for r in t)


def test_default_transitions_door_has_closed_to_open():
    from dungeon_daddy.ui.panels.campaign_edit_panel import default_transitions_for_archetype
    t = default_transitions_for_archetype("door")
    assert any(r["from_state"] == "closed" and r["to_state"] == "open" for r in t)


def test_default_transitions_unknown_archetype_returns_empty():
    from dungeon_daddy.ui.panels.campaign_edit_panel import default_transitions_for_archetype
    assert default_transitions_for_archetype("nonexistent") == []


# ---------------------------------------------------------------------------
# CampaignListPanel — rooms section
# ---------------------------------------------------------------------------


def test_section_labels_includes_rooms_key():
    from dungeon_daddy.ui.panels.campaign_list_panel import _SECTION_LABELS
    assert "rooms" in _SECTION_LABELS


def test_draw_card_rooms_with_room_object_routes_to_room_object_card(mocker):
    p = _list_panel(1)
    mock_ro_card = mocker.patch.object(p, "_draw_room_object_card")
    mocker.patch("dungeon_daddy.ui.panels.campaign_list_panel.draw_rounded_rect")
    mocker.patch("arcade.draw_text")
    obj = _make_room_object()
    p._draw_card("rooms", obj, 0, 220, 300, 460, 80, hovered=False)
    mock_ro_card.assert_called_once()
