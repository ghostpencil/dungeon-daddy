from __future__ import annotations

from dungeon_daddy.memory.dungeon_exchange import record_dungeon_exchange
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ClockState


def _intimacy_clock(filled: int = 3, segments: int = 6) -> ClockState:
    return ClockState(
        clock_id="clk_intim",
        campaign_id="camp_001",
        label="Dungeon Intimacy",
        segments=segments,
        filled=filled,
        category="dungeon_intimacy",
        clock_level="dungeon",
        monotonic=False,
    )


class TestRecordDungeonExchange:
    def test_drafts_a_memory_summarizing_the_exchange(
        self, repo: MemoryRepository
    ) -> None:
        result = record_dungeon_exchange(
            repo,
            campaign_id="camp_001",
            actor="mara",
            player_message="Who built you?",
            dungeon_reply="I remember hands, but not faces.",
        )

        entry = repo.get_memory_entry(result.memory_id)
        assert entry is not None
        assert entry["campaign_id"] == "camp_001"
        assert entry["status"] == "draft"
        assert entry["type"] in ("dungeon_state", "relationship")
        assert "Who built you?" in entry["summary"]
        assert "I remember hands, but not faces." in entry["summary"]

    def test_writes_only_drafts_never_an_authoritative_entry(
        self, repo: MemoryRepository
    ) -> None:
        # D6 / authority boundary: the engine may only draft memory for an
        # exchange — approval flows through the curation path, never a direct
        # authoritative write.
        record_dungeon_exchange(
            repo,
            campaign_id="camp_001",
            actor="mara",
            player_message="Tell me your name.",
            dungeon_reply="Names are leashes. I wear none.",
        )

        counts = repo.count_by_status("camp_001")
        assert counts == {"draft": 1}

    def test_does_not_advance_the_intimacy_clock(
        self, repo: MemoryRepository
    ) -> None:
        # Phase 51.5 (D1, D5): chat no longer ticks intimacy — the objective
        # service (advance_objectives) is the single intimacy-tick source. A
        # pre-existing intimacy clock is left untouched by a dungeon exchange.
        clock = _intimacy_clock(filled=3, segments=6)
        repo.save_clock(
            clock.clock_id, clock.campaign_id, clock.label, clock.segments,
            clock.filled, category="dungeon_intimacy", monotonic=False,
        )

        record_dungeon_exchange(
            repo,
            campaign_id="camp_001",
            actor="mara",
            player_message="Who built you?",
            dungeon_reply="I remember hands, but not faces.",
        )

        persisted = repo.get_clocks("camp_001")[0]
        assert persisted["filled"] == 3  # unchanged — no tick
