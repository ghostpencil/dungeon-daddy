"""Tests for playbook picker in CampaignEditPanel actor form — Phase 49 Slice 5."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dungeon_daddy.campaign.manifest import ActorManifest
from dungeon_daddy.ui.panels.campaign_edit_panel import CampaignEditPanel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _edit_panel() -> CampaignEditPanel:
    panel = CampaignEditPanel.__new__(CampaignEditPanel)
    panel._x = 0.0
    panel._y = 0.0
    panel._w = 300.0
    panel._h = 900.0
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


def _actor(playbook_slug: str | None = None, **kwargs: object) -> ActorManifest:
    defaults: dict = dict(
        slug="protagonist",
        display_name="Hero",
        actor_type="pc",
        concept="A brave adventurer",
    )
    defaults.update(kwargs)
    actor = ActorManifest(**defaults)
    actor.playbook_slug = playbook_slug
    return actor


def _show_actor(panel: CampaignEditPanel, actor: ActorManifest, *, is_new: bool = False) -> None:
    mock_widget = MagicMock()
    mock_widget.text = ""
    with (
        patch("arcade.gui.UIInputText", return_value=mock_widget),
        patch("arcade.gui.UIFlatButton", return_value=MagicMock()),
    ):
        panel.show_actor(actor, lambda d: None, lambda: None, is_new=is_new)


# ---------------------------------------------------------------------------
# Cycle 31 — Tracer: form registers a playbook choice picker
# ---------------------------------------------------------------------------


def test_actor_form_has_playbook_picker():
    panel = _edit_panel()
    _show_actor(panel, _actor())
    assert "playbook" in panel._choice_values


# ---------------------------------------------------------------------------
# Cycle 32 — Options: 5 entries (sentinel + 4 slugs)
# ---------------------------------------------------------------------------


def test_actor_form_playbook_options_has_five_entries():
    panel = _edit_panel()
    _show_actor(panel, _actor())
    assert len(panel._choice_options["playbook"]) == 5


def test_actor_form_playbook_options_starts_with_none_sentinel():
    panel = _edit_panel()
    _show_actor(panel, _actor())
    assert panel._choice_options["playbook"][0] == "none"


def test_actor_form_playbook_options_contains_four_slugs():
    panel = _edit_panel()
    _show_actor(panel, _actor())
    options = panel._choice_options["playbook"]
    for slug in ("fighter", "thief", "priest", "artificer"):
        assert slug in options


# ---------------------------------------------------------------------------
# Cycle 33 — No playbook selected → playbook_slug is None in collected data
# ---------------------------------------------------------------------------


def test_collect_inputs_returns_playbook_slug_none_when_none_selected():
    panel = _edit_panel()
    _show_actor(panel, _actor())
    panel._choice_values["playbook"] = 0  # sentinel
    data = panel._collect_inputs()
    assert data.get("playbook_slug") is None


# ---------------------------------------------------------------------------
# Cycle 34 — Actor with playbook_slug pre-selects the picker
# ---------------------------------------------------------------------------


def test_actor_with_playbook_preselects_picker():
    panel = _edit_panel()
    _show_actor(panel, _actor(playbook_slug="fighter"))
    idx = panel._choice_values["playbook"]
    assert panel._choice_options["playbook"][idx] == "fighter"


# ---------------------------------------------------------------------------
# Cycle 35 — Picker at fighter index → collect returns playbook_slug = "fighter"
# ---------------------------------------------------------------------------


def test_collect_inputs_returns_correct_playbook_slug():
    panel = _edit_panel()
    _show_actor(panel, _actor())
    options = panel._choice_options["playbook"]
    panel._choice_values["playbook"] = options.index("fighter")
    data = panel._collect_inputs()
    assert data["playbook_slug"] == "fighter"


# ---------------------------------------------------------------------------
# Cycle 36 — Form with fighter playbook pre-populates action ratings
# ---------------------------------------------------------------------------


def test_actor_with_fighter_playbook_prepopulates_fight_rating():
    panel = _edit_panel()
    _show_actor(panel, _actor(playbook_slug="fighter"))
    assert panel._number_values.get("rating_fight") == 2


def test_actor_with_fighter_playbook_prepopulates_endure_rating():
    panel = _edit_panel()
    _show_actor(panel, _actor(playbook_slug="fighter"))
    assert panel._number_values.get("rating_endure") == 2


def test_actor_with_fighter_playbook_sets_non_emphasis_ratings_from_playbook():
    panel = _edit_panel()
    _show_actor(panel, _actor(playbook_slug="fighter"))
    assert panel._number_values.get("rating_tinker") == 0


# ---------------------------------------------------------------------------
# Cycle 37 — Form with fighter playbook pre-populates stress tracks
# ---------------------------------------------------------------------------


def test_actor_with_fighter_playbook_populates_body_stress_track():
    panel = _edit_panel()
    _show_actor(panel, _actor(playbook_slug="fighter"))
    # Fighter has body capacity 4
    assert panel._number_values.get("stress_body") == 4


def test_actor_with_fighter_playbook_populates_all_stress_track_keys():
    panel = _edit_panel()
    _show_actor(panel, _actor(playbook_slug="fighter"))
    for key in ("body", "composure", "bonds", "weird"):
        assert f"stress_{key}" in panel._number_values
