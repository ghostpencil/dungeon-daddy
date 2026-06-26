from dungeon_daddy.rpg.dungeon_channel import (
    REASON_NOT_HERE,
    REASON_NOT_INTIMATE,
    dungeon_channel_available,
)
from dungeon_daddy.rpg.models import ClockState


def _intimacy(**kwargs) -> ClockState:  # type: ignore[no-untyped-def]
    defaults = dict(
        clock_id="intimacy",
        campaign_id="c1",
        label="The Dungeon Knows You",
        segments=6,
        filled=3,
        category="dungeon_intimacy",
        clock_level="dungeon",
        monotonic=False,
    )
    defaults.update(kwargs)
    return ClockState(**defaults)


def _room(resonance_point: bool) -> dict:
    return {"room_id": "R1", "resonance_point": resonance_point}


def test_open_when_resonance_and_intimacy_at_threshold() -> None:
    available, reason = dungeon_channel_available(_room(True), _intimacy(filled=3))
    assert available is True
    assert reason is None


def test_closed_when_not_a_resonance_point() -> None:
    available, reason = dungeon_channel_available(_room(False), _intimacy(filled=6))
    assert available is False
    assert reason == REASON_NOT_HERE


def test_closed_when_intimacy_below_threshold() -> None:
    available, reason = dungeon_channel_available(_room(True), _intimacy(filled=2))
    assert available is False
    assert reason == REASON_NOT_INTIMATE


def test_closed_when_intimacy_clock_absent() -> None:
    available, reason = dungeon_channel_available(_room(True), None)
    assert available is False
    assert reason == REASON_NOT_INTIMATE


def test_open_at_exact_threshold_boundary() -> None:
    # 3/6 == 0.5 == INTIMACY_THRESHOLD — at threshold counts as open (>=).
    available, _ = dungeon_channel_available(_room(True), _intimacy(segments=6, filled=3))
    assert available is True


def test_not_here_takes_precedence_when_both_gates_fail() -> None:
    available, reason = dungeon_channel_available(_room(False), None)
    assert available is False
    assert reason == REASON_NOT_HERE
