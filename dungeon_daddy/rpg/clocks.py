from __future__ import annotations

import uuid

from dungeon_daddy.rpg.models import ClockState


def create_clock(
    campaign_id: str,
    label: str,
    segments: int,
    clock_id: str | None = None,
) -> ClockState:
    return ClockState(
        clock_id=clock_id or str(uuid.uuid4()),
        campaign_id=campaign_id,
        label=label,
        segments=segments,
    )


def advance_clock(clock: ClockState, ticks: int) -> ClockState:
    new_filled = clock.filled + ticks
    if new_filled >= clock.segments:
        return clock.model_copy(update={"filled": clock.segments, "status": "completed"})
    return clock.model_copy(update={"filled": new_filled})


def tick_clock(clock: ClockState, delta: int) -> ClockState:
    """Move a clock by a signed delta, clamping filled to [0, segments].

    A monotonic clock latches ``status="completed"`` when it reaches the top
    (the existing :func:`advance_clock` behavior). A non-monotonic clock may
    recede and never latches — its thresholds are read live by callers.
    """
    new_filled = max(0, min(clock.segments, clock.filled + delta))
    if clock.monotonic and new_filled >= clock.segments:
        return clock.model_copy(update={"filled": clock.segments, "status": "completed"})
    return clock.model_copy(update={"filled": new_filled})
