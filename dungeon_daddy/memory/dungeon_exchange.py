"""Engine side-effect per dungeon-channel exchange (spec §4.7).

Authoritative, engine-applied — never the LLM. After each dungeon reply the
engine drafts a ``MemoryEntry`` summarizing the exchange.

Phase 51.5 (D1, D5): intimacy is **no longer advanced here**. Chat exchanges
stopped ticking intimacy — the objective service (``rpg.objectives.
advance_objectives``) is the single intimacy-tick source. This service only
drafts a memory of the exchange (status ``draft``; curation approves it later,
never the LLM — authority boundary / D6).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from dungeon_daddy.memory.repository import MemoryRepository

# The exchange deepens the player's relationship with the dungeon; drafts are of
# the ``relationship`` memory type (one of the canonical types per D4).
DUNGEON_EXCHANGE_MEMORY_TYPE = "relationship"


@dataclass(frozen=True)
class DungeonExchangeResult:
    """Outcome of recording one dungeon exchange."""

    memory_id: str


def record_dungeon_exchange(
    repo: MemoryRepository,
    *,
    campaign_id: str,
    actor: str,
    player_message: str,
    dungeon_reply: str,
) -> DungeonExchangeResult:
    """Draft a memory of one dungeon-channel exchange (no intimacy tick).

    Per Phase 51.5 (D1/D5) chat no longer advances intimacy — the objective
    service is the single tick source. This service only drafts a ``MemoryEntry``
    summarizing the exchange (status ``draft``; the LLM never authors
    authoritative memory — D6).
    """
    memory_id = str(uuid.uuid4())
    repo.save_memory_entry(
        memory_id=memory_id,
        campaign_id=campaign_id,
        entry_type=DUNGEON_EXCHANGE_MEMORY_TYPE,
        title=f"{actor} spoke with the dungeon",
        summary=(
            f"{actor} said: {player_message}\n"
            f"The dungeon answered: {dungeon_reply}"
        ),
        status="draft",
    )
    return DungeonExchangeResult(memory_id=memory_id)
