"""Unit tests for CampaignNavPanel, CampaignListPanel, and CampaignEditPanel — Phase 42/43."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dungeon_daddy.campaign.manifest import FactionManifest
from dungeon_daddy.ui.panels.campaign_edit_panel import CampaignEditPanel
from dungeon_daddy.ui.panels.campaign_nav_panel import CampaignNavPanel
from dungeon_daddy.ui.panels.campaign_list_panel import CampaignListPanel


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
# CampaignNavPanel button hit-tests
# ---------------------------------------------------------------------------
#
# Panel: x=0, y=0, w=220
# _BTN_H=26, _BTN_PAD=8
# Save button: cx=110, cy=8+13=21, w=204 → y ∈ [8, 34]
# Load/New:    btn_w=(220-24)/2=98; cy=8+26+8+13=55 → y ∈ [42, 68]
#   load_cx = 0+8+49=57  → x ∈ [8, 106]
#   new_cx  = 0+8+98+8+49=163 → x ∈ [114, 212]

def test_save_btn_at_centre_returns_true():
    p = _nav_panel()
    assert p.save_btn_at(110, 21) is True


def test_save_btn_at_outside_returns_false():
    p = _nav_panel()
    assert p.save_btn_at(110, 50) is False


def test_load_btn_at_centre_returns_true():
    p = _nav_panel()
    assert p.load_btn_at(57, 55) is True


def test_load_btn_at_outside_returns_false():
    p = _nav_panel()
    # x=163 is in the new button zone, not load
    assert p.load_btn_at(163, 55) is False


def test_new_btn_at_centre_returns_true():
    p = _nav_panel()
    assert p.new_btn_at(163, 55) is True


def test_new_btn_at_outside_returns_false():
    p = _nav_panel()
    assert p.new_btn_at(57, 55) is False


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
    p.set_scroll_offset(88)  # shift cards up by 88px
    assert p.item_at(400, 234) == 0
    assert p.item_at(400, 146) == 1


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
    p.set_scroll_offset(88)
    # item 0 top after scroll = 362-88=274; zone y ∈ [250, 266]
    assert p.delete_zone_at(664, 258) == 0


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
