import pytest
from pydantic import ValidationError

from dungeon_daddy.memory.models import ContextBundle, DomainEvent, MemoryEntry


class TestMemoryEntry:
    def test_constructs_with_required_fields(self) -> None:
        e = MemoryEntry(memory_id="mem_1", campaign_id="camp_1", type="fallout", title="Haunted")
        assert e.memory_id == "mem_1"
        assert e.status == "draft"

    def test_status_defaults_to_draft(self) -> None:
        e = MemoryEntry(memory_id="x", campaign_id="c", type="note", title="T")
        assert e.status == "draft"

    def test_summary_defaults_to_empty(self) -> None:
        e = MemoryEntry(memory_id="x", campaign_id="c", type="note", title="T")
        assert e.summary == ""

    def test_importance_defaults_to_five(self) -> None:
        e = MemoryEntry(memory_id="x", campaign_id="c", type="note", title="T")
        assert e.importance == 5

    def test_tags_default_to_empty_list(self) -> None:
        e = MemoryEntry(memory_id="x", campaign_id="c", type="note", title="T")
        assert e.tags == []

    def test_status_values(self) -> None:
        for s in ("draft", "approved", "rejected", "archived"):
            e = MemoryEntry(memory_id="x", campaign_id="c", type="note", title="T", status=s)
            assert e.status == s

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MemoryEntry(memory_id="x", campaign_id="c", type="note", title="T", status="deleted")


class TestDomainEvent:
    def test_constructs_with_required_fields(self) -> None:
        e = DomainEvent(
            event_id="evt_1", campaign_id="camp_1", event_type="action.resolved"
        )
        assert e.event_type == "action.resolved"

    def test_occurred_at_auto_set(self) -> None:
        e = DomainEvent(event_id="e", campaign_id="c", event_type="scene.started")
        assert e.occurred_at is not None

    def test_payload_defaults_to_empty_dict(self) -> None:
        e = DomainEvent(event_id="e", campaign_id="c", event_type="scene.started")
        assert e.payload == {}

    def test_payload_accepts_arbitrary_dict(self) -> None:
        e = DomainEvent(
            event_id="e",
            campaign_id="c",
            event_type="action.resolved",
            payload={"actor_id": "pc_mara", "outcome": "full"},
        )
        assert e.payload["outcome"] == "full"


class TestContextBundle:
    def test_constructs_with_required_fields(self) -> None:
        b = ContextBundle(
            bundle_id="bun_1",
            campaign_id="camp_1",
            mode="run_scene",
        )
        assert b.bundle_id == "bun_1"
        assert b.scene_id is None

    def test_all_modes_accepted(self) -> None:
        for m in ("run_scene", "recap", "room_revisit", "fallout_resolution"):
            b = ContextBundle(bundle_id="b", campaign_id="c", mode=m)
            assert b.mode == m

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ContextBundle(bundle_id="b", campaign_id="c", mode="freeform")

    def test_collections_default_to_empty(self) -> None:
        b = ContextBundle(bundle_id="b", campaign_id="c", mode="recap")
        assert b.active_fallout == []
        assert b.open_clocks == []
        assert b.must_remember == []
        assert b.memory_cards == []
