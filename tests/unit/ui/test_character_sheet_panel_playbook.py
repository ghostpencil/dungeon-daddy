"""Slice 6 — CharacterSheetPanel playbook section (Cycles 43–50)."""
from __future__ import annotations

import pytest

from dungeon_daddy.rpg.playbook import (
    Playbook, PlaybookKit, PlaybookAbility, PlaybookStressTrack, SignatureAdverb,
)
from dungeon_daddy.rpg.models import ActorAbility, ActorState


def _panel():
    from dungeon_daddy.ui.panels.character_sheet_panel import CharacterSheetPanel
    return CharacterSheetPanel()


def _playbook(**kw) -> Playbook:
    defaults = dict(
        slug="fighter",
        display_name="Fighter",
        starting_action_ratings={"fight": 2, "endure": 2, "move": 1},
        starting_stress_tracks=[
            PlaybookStressTrack(track_key="body", capacity=4),
        ],
        starting_kit=PlaybookKit(
            slug="combat-gear",
            display_name="Combat Gear",
            description="A fighter's standard kit.",
            charges_max=3,
            abilities=[
                PlaybookAbility(
                    slug="press-the-attack",
                    display_name="Press the Attack",
                    description="Push through and strike again.",
                )
            ],
        ),
        tags=["warrior", "frontline"],
        signature_adverbs=[
            SignatureAdverb(slug="recklessly", target_types=["npc", "monster"]),
            SignatureAdverb(slug="brutally", target_types=["npc", "monster"]),
        ],
        starting_abilities=["press-the-attack"],
        ability_pool=[],
    )
    defaults.update(kw)
    return Playbook(**defaults)


def _actor(**kw) -> ActorState:
    defaults = dict(
        actor_id="a1",
        campaign_id="c1",
        actor_type="pc",
        slug="hero",
        display_name="Elara",
    )
    defaults.update(kw)
    return ActorState(**defaults)


def _ability(**kw) -> ActorAbility:
    defaults = dict(
        actor_id="a1",
        ability_slug="press-the-attack",
        display_name="Press the Attack",
        description="Push through and strike again.",
        source="kit",
    )
    defaults.update(kw)
    return ActorAbility(**defaults)


# ---------------------------------------------------------------------------
# Cycle 43 — _playbook defaults None; set_playbook stores it
# ---------------------------------------------------------------------------

def test_playbook_default_none():
    panel = _panel()
    assert panel._playbook is None


def test_set_playbook_stores_playbook():
    panel = _panel()
    pb = _playbook()
    panel.set_playbook(pb)
    assert panel._playbook is pb
    assert panel._playbook.display_name == "Fighter"


# ---------------------------------------------------------------------------
# Cycle 44 — set_playbook(None) clears
# ---------------------------------------------------------------------------

def test_set_playbook_none_clears():
    panel = _panel()
    panel.set_playbook(_playbook())
    panel.set_playbook(None)
    assert panel._playbook is None


# ---------------------------------------------------------------------------
# Cycle 45 — _abilities defaults []; set_abilities stores list
# ---------------------------------------------------------------------------

def test_abilities_default_empty():
    panel = _panel()
    assert panel._abilities == []


def test_set_abilities_stores_list():
    panel = _panel()
    ab = _ability()
    panel.set_abilities([ab])
    assert len(panel._abilities) == 1
    assert panel._abilities[0].display_name == "Press the Attack"


# ---------------------------------------------------------------------------
# Cycle 46 — set_abilities([]) replaces previous
# ---------------------------------------------------------------------------

def test_set_abilities_replaces_previous():
    panel = _panel()
    panel.set_abilities([_ability()])
    panel.set_abilities([])
    assert panel._abilities == []


# ---------------------------------------------------------------------------
# Cycle 47 — draw() emits playbook display name when playbook is set
# ---------------------------------------------------------------------------

def test_draw_renders_playbook_name(mocker):
    panel = _panel()
    panel.setup(0, 0, 200, 600)
    panel.set_actor(_actor())
    panel.set_playbook(_playbook(display_name="Fighter"))

    mock_arcade = mocker.patch("dungeon_daddy.ui.panels.character_sheet_panel.arcade")
    panel.draw()

    texts = [
        call.args[0]
        for call in mock_arcade.draw_text.call_args_list
        if call.args
    ]
    assert any("Fighter" in t for t in texts)


# ---------------------------------------------------------------------------
# Cycle 48 — draw() skips playbook section when _playbook is None
# ---------------------------------------------------------------------------

def test_draw_skips_playbook_section_when_none(mocker):
    panel = _panel()
    panel.setup(0, 0, 200, 600)
    # No set_playbook call

    mock_arcade = mocker.patch("dungeon_daddy.ui.panels.character_sheet_panel.arcade")
    panel.draw()

    texts = [
        call.args[0]
        for call in mock_arcade.draw_text.call_args_list
        if call.args
    ]
    assert not any("PLAYBOOK" in t for t in texts)


# ---------------------------------------------------------------------------
# Cycle 49 — draw() renders each signature adverb slug
# ---------------------------------------------------------------------------

def test_draw_renders_signature_adverbs(mocker):
    panel = _panel()
    panel.setup(0, 0, 200, 600)
    panel.set_actor(_actor())
    panel.set_playbook(_playbook())

    mock_arcade = mocker.patch("dungeon_daddy.ui.panels.character_sheet_panel.arcade")
    panel.draw()

    texts = [
        call.args[0]
        for call in mock_arcade.draw_text.call_args_list
        if call.args
    ]
    assert any("recklessly" in t for t in texts)
    assert any("brutally" in t for t in texts)


# ---------------------------------------------------------------------------
# Cycle 50 — draw() renders each ability display name
# ---------------------------------------------------------------------------

def test_draw_renders_ability_display_names(mocker):
    panel = _panel()
    panel.setup(0, 0, 200, 600)
    panel.set_actor(_actor())
    panel.set_abilities([
        _ability(ability_slug="press-the-attack", display_name="Press the Attack"),
        _ability(ability_slug="iron-will", display_name="Iron Will"),
    ])

    mock_arcade = mocker.patch("dungeon_daddy.ui.panels.character_sheet_panel.arcade")
    panel.draw()

    texts = [
        call.args[0]
        for call in mock_arcade.draw_text.call_args_list
        if call.args
    ]
    assert any("Press the Attack" in t for t in texts)
    assert any("Iron Will" in t for t in texts)
