from __future__ import annotations

from dungeon_daddy.rpg.models import StressTrack

_PC_TRACKS = ("body", "composure", "bonds", "weird")
_DEFAULT_CAPACITY = 4


def create_default_stress_tracks() -> dict[str, StressTrack]:
    return {key: StressTrack(track_key=key, capacity=_DEFAULT_CAPACITY) for key in _PC_TRACKS}


def mark_stress(track: StressTrack, amount: int = 1) -> StressTrack:
    new_filled = min(track.filled + amount, track.capacity)
    return track.model_copy(update={"filled": new_filled})


def is_track_filled(track: StressTrack) -> bool:
    return track.filled >= track.capacity
