"""Tests for the Level 2 Crucible seed (`populate_crucible_level2`).

The Great Lift is one physical object that spans levels. It is modelled once as a
load-bearing ``mechanism`` on Level 1 (R4, the object that gates the vertical
exit). The Level 2 upper landing is a *scenery* presence only — it must not be a
second reported subsystem, or the dungeon's truthful systems assessment lists the
lift twice (and the LLM collapses the duplicate, dropping a state).
"""
from dungeon_daddy.rpg.dungeon_channel import (
    SUBSYSTEM_ARCHETYPES,
    dungeon_systems_status,
)
from tools.populate_crucible_level2 import _great_lift_upper


def test_upper_landing_is_scenery_not_a_subsystem():
    upper = _great_lift_upper()
    assert upper.archetype not in SUBSYSTEM_ARCHETYPES


def test_upper_landing_drops_out_of_systems_status():
    upper = _great_lift_upper()
    obj = {
        "display_name": upper.display_name,
        "archetype": upper.archetype,
        "current_state": upper.current_state,
    }
    assert dungeon_systems_status([obj]) == []
