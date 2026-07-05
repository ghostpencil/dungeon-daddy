from dungeon_daddy.rpg.models import StressTrack
from dungeon_daddy.rpg.stress import (
    create_default_stress_tracks,
    is_track_filled,
    mark_stress,
)


def test_create_default_stress_tracks_returns_four_tracks() -> None:
    tracks = create_default_stress_tracks()
    assert set(tracks.keys()) == {"body", "composure", "bonds", "weird"}
    for track in tracks.values():
        assert track.capacity == 4
        assert track.filled == 0


def test_mark_stress_increases_filled() -> None:
    track = StressTrack(track_key="body", capacity=4, filled=1)
    updated = mark_stress(track, amount=2)
    assert updated.filled == 3


def test_is_track_filled_false_when_not_full() -> None:
    track = StressTrack(track_key="weird", capacity=4, filled=3)
    assert is_track_filled(track) is False


def test_is_track_filled_true_when_at_capacity() -> None:
    track = StressTrack(track_key="weird", capacity=4, filled=4)
    assert is_track_filled(track) is True


def test_mark_stress_clamps_at_capacity() -> None:
    track = StressTrack(track_key="composure", capacity=4, filled=3)
    updated = mark_stress(track, amount=5)
    assert updated.filled == 4
