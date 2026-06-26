from dungeon_daddy.rpg.clocks import advance_clock, create_clock, tick_clock
from dungeon_daddy.rpg.models import ClockState


def _clock(**kwargs) -> ClockState:  # type: ignore[no-untyped-def]
    defaults = dict(
        clock_id="ck1",
        campaign_id="c1",
        label="Open the Choir Door",
        segments=6,
        filled=0,
    )
    defaults.update(kwargs)
    return ClockState(**defaults)


def test_advance_clock_increments_filled() -> None:
    clock = _clock(filled=0)
    updated = advance_clock(clock, ticks=2)
    assert updated.filled == 2
    assert updated.status == "active"


def test_advance_clock_to_completion() -> None:
    clock = _clock(segments=4, filled=3)
    updated = advance_clock(clock, ticks=1)
    assert updated.filled == 4
    assert updated.status == "completed"


def test_advance_clock_overflow_clamps_to_segments() -> None:
    clock = _clock(segments=4, filled=2)
    updated = advance_clock(clock, ticks=10)
    assert updated.filled == 4
    assert updated.status == "completed"


def test_tick_clock_positive_delta_increments() -> None:
    clock = _clock(segments=6, filled=1)
    updated = tick_clock(clock, 2)
    assert updated.filled == 3
    assert updated.status == "active"


def test_tick_clock_monotonic_latches_completed_at_full() -> None:
    clock = _clock(segments=4, filled=3, monotonic=True)
    updated = tick_clock(clock, 5)
    assert updated.filled == 4
    assert updated.status == "completed"


def test_tick_clock_negative_delta_clamps_to_zero() -> None:
    clock = _clock(segments=6, filled=2)
    updated = tick_clock(clock, -5)
    assert updated.filled == 0
    assert updated.status == "active"


def test_tick_clock_non_monotonic_does_not_latch_at_full() -> None:
    clock = _clock(segments=4, filled=3, monotonic=False)
    updated = tick_clock(clock, 1)
    assert updated.filled == 4
    assert updated.status == "active"


def test_tick_clock_non_monotonic_can_recede() -> None:
    clock = _clock(segments=6, filled=5, monotonic=False)
    updated = tick_clock(clock, -2)
    assert updated.filled == 3
    assert updated.status == "active"


def test_create_clock_defaults() -> None:
    clock = create_clock(campaign_id="c1", label="Escape", segments=6)
    assert clock.segments == 6
    assert clock.filled == 0
    assert clock.status == "active"
    assert clock.campaign_id == "c1"
