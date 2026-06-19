"""Fog-of-war helpers for the Play-mode map (Phase 48 Slice 10).

Thin presentation logic over the authoritative ``session.visited_rooms`` list.
A destination room's name is only revealed once the party has entered it; until
then the map shows ``?`` (the exit's label/direction is still shown by the
caller). Throwaway UI — replaced by Phase 50's Card map treatment.
"""
from __future__ import annotations

from collections.abc import Iterable

HIDDEN_LABEL = "?"


def fog_of_war_label(*, room_id: str, room_name: str, visited_rooms: Iterable[str]) -> str:
    return room_name if room_id in set(visited_rooms) else HIDDEN_LABEL
