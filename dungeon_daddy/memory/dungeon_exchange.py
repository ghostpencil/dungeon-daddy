"""Engine side-effects per dungeon-channel exchange (spec §4.7 / Phase 51 Slice 7).

Authoritative, engine-applied — never the LLM. After each dungeon reply the
engine ticks the (non-monotonic) intimacy clock and drafts a ``MemoryEntry``
summarizing the exchange. The LLM only narrates; it does not advance clocks or
author authoritative memory (authority boundary / decision D6).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.clocks import tick_clock
from dungeon_daddy.rpg.models import ClockState

# Per-exchange intimacy advance (the dungeon learns a little about you each time
# you speak). Conservative default — an open §6 balance question; see
# spec/PHASE_51_TALK_TO_THE_DUNGEON.md §6 and BALANCE_NOTES.md when tuning.
DUNGEON_EXCHANGE_INTIMACY_DELTA = 1

# The exchange deepens the player's relationship with the dungeon; drafts are of
# the ``relationship`` memory type (one of the canonical types per D4).
DUNGEON_EXCHANGE_MEMORY_TYPE = "relationship"


@dataclass(frozen=True)
class DungeonExchangeResult:
    """Outcome of recording one dungeon exchange."""

    clock: ClockState
    memory_id: str


def record_dungeon_exchange(
    repo: MemoryRepository,
    *,
    intimacy_clock: ClockState,
    actor: str,
    player_message: str,
    dungeon_reply: str,
    delta: int = DUNGEON_EXCHANGE_INTIMACY_DELTA,
) -> DungeonExchangeResult:
    """Apply the engine side-effects of one dungeon-channel exchange.

    Ticks and persists the intimacy clock (non-monotonic, may recede on other
    paths; here it advances). Returns the updated clock.
    """
    ticked = tick_clock(intimacy_clock, delta)
    repo.update_clock_progress(ticked.clock_id, ticked.filled, ticked.status)

    memory_id = str(uuid.uuid4())
    repo.save_memory_entry(
        memory_id=memory_id,
        campaign_id=intimacy_clock.campaign_id,
        entry_type=DUNGEON_EXCHANGE_MEMORY_TYPE,
        title=f"{actor} spoke with the dungeon",
        summary=(
            f"{actor} said: {player_message}\n"
            f"The dungeon answered: {dungeon_reply}"
        ),
        status="draft",
    )
    return DungeonExchangeResult(clock=ticked, memory_id=memory_id)
