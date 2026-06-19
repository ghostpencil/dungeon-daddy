"""Contextual `how?` chip builder for the Play-mode exit list (Phase 48 Slice 10).

Throwaway UI helper. The durable contract is the engine's
``HOW_MODIFIER_FLAGS`` table in ``rpg/move_party.py`` — this module only decides
which of those chips to *surface* for a given exit/room context. Chips are
restricted to keys that have a real flag mapping so the UI never offers an
adverb the engine cannot resolve.
"""
from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.rpg.move_party import HOW_MODIFIER_FLAGS

# Always offered for an ordinary exit.
_BASE_CHIPS: list[str] = ["cautiously", "quickly", "boldly"]


@dataclass
class HowChipData:
    how: str
    label: str


def build_how_chips(
    *,
    max_sense: int = 0,
    one_way: bool = False,
    ritual_connector: bool = False,
    armed_trap_clock: bool = False,
) -> list[HowChipData]:
    keys = list(_BASE_CHIPS)
    if max_sense >= 1:
        keys.append("stealthily")
    if one_way:
        keys.append("deliberately")
    if ritual_connector:
        keys.append("reverently")
    if armed_trap_clock:
        keys.append("recklessly")
    # Surface only chips the engine can actually resolve.
    keys = [k for k in keys if k in HOW_MODIFIER_FLAGS]
    return [HowChipData(how=key, label=key.capitalize()) for key in keys]
