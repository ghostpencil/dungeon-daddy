"""Engine side-effect per dungeon-channel exchange (spec §4.7).

Authoritative, engine-applied — never the LLM. After each dungeon reply the
engine records a ``MemoryEntry`` summarizing the exchange.

Phase 51.5 (D1, D5): intimacy is **no longer advanced here**. Chat exchanges
stopped ticking intimacy — the objective service (``rpg.objectives.
advance_objectives``) is the single intimacy-tick source. This service only
records a memory of the exchange.

Owner override (2026-06-28): dungeon-generated memories are now written
**approved** rather than ``draft``. The player is no longer asked to curate the
dungeon's own recollections, and an approved memory feeds back through
``MemoryRetriever`` so the dungeon remembers past sittings (fixes cross-session
amnesia). This relaxes the D6 *curation* gate only — the LLM still never writes
memory; the engine composes a factual record of what was said.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import scene_memory_tags

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
    room_id: str | None = None,
    party_ids: Sequence[str] | None = None,
) -> DungeonExchangeResult:
    """Record an approved memory of one dungeon-channel exchange (no intimacy tick).

    Per Phase 51.5 (D1/D5) chat no longer advances intimacy — the objective
    service is the single tick source. This service records a ``MemoryEntry``
    summarizing the exchange as **approved** (owner override 2026-06-28): the
    dungeon's recollections are no longer queued for player curation, and being
    approved they feed back through ``MemoryRetriever``.
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
        status="approved",
    )
    # A5b: stamp the scene anchors (current-room location + present-actor tags)
    # so A5 scoped retrieval resurfaces this exchange in the same scene later.
    for tag in scene_memory_tags(repo, campaign_id, room_id, party_ids or []):
        repo.add_memory_tag(memory_id, tag)
    return DungeonExchangeResult(memory_id=memory_id)
