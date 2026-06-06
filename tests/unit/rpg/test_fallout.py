import pytest

from dungeon_daddy.rpg.fallout import evaluate_fallout, get_catalog_entry
from dungeon_daddy.rpg.models import ActorState, FalloutRecord, StressTrack
from tests.unit.rpg._factories import make_pc as _pc_factory


def _pc(actor_id: str = "pc_1", campaign_id: str = "camp_1") -> ActorState:
    return _pc_factory(actor_id, campaign_id, body=4)


def test_evaluate_fallout_returns_fallout_record_for_filled_body_track() -> None:
    actor = _pc()
    record, _ = evaluate_fallout(actor, "body", "camp_1")
    assert isinstance(record, FalloutRecord)
    assert record.track_key == "body"
    assert record.actor_id == "pc_1"
    assert record.campaign_id == "camp_1"


def test_severity_is_minor_with_no_existing_fallout() -> None:
    actor = _pc()
    record, _ = evaluate_fallout(actor, "body", "camp_1")
    assert record.severity == "minor"


def test_severity_is_moderate_with_one_active_fallout_on_same_track() -> None:
    actor = _pc()
    existing = [
        FalloutRecord(
            fallout_id="f1",
            campaign_id="camp_1",
            actor_id="pc_1",
            track_key="body",
            severity="minor",
            title="Battered",
            summary="...",
            status="active",
        )
    ]
    record, _ = evaluate_fallout(actor, "body", "camp_1", existing_fallout=existing)
    assert record.severity == "moderate"


def test_severity_is_severe_with_two_or_more_active_fallout_on_same_track() -> None:
    actor = _pc()
    existing = [
        FalloutRecord(
            fallout_id="f1",
            campaign_id="camp_1",
            actor_id="pc_1",
            track_key="body",
            severity="minor",
            title="Battered",
            summary="...",
            status="active",
        ),
        FalloutRecord(
            fallout_id="f2",
            campaign_id="camp_1",
            actor_id="pc_1",
            track_key="body",
            severity="moderate",
            title="Wounded",
            summary="...",
            status="active",
        ),
    ]
    record, _ = evaluate_fallout(actor, "body", "camp_1", existing_fallout=existing)
    assert record.severity == "severe"


def test_get_catalog_entry_body_minor_returns_non_empty_title_and_summary() -> None:
    title, summary = get_catalog_entry("body", "minor")
    assert title
    assert summary


@pytest.mark.parametrize(
    "track,severity",
    [
        (t, s)
        for t in ("body", "composure", "bonds", "weird")
        for s in ("minor", "moderate", "severe")
    ],
)
def test_all_twelve_catalog_entries_are_non_empty(track: str, severity: str) -> None:
    title, summary = get_catalog_entry(track, severity)
    assert title
    assert summary


def test_stress_track_is_reset_to_zero_after_fallout() -> None:
    actor = _pc()
    assert actor.stress["body"].filled == 4
    _, reset_track = evaluate_fallout(actor, "body", "camp_1")
    assert reset_track.filled == 0
    assert reset_track.track_key == "body"


def test_weird_fallout_has_dungeon_influence_flag() -> None:
    actor = _pc()
    actor = actor.model_copy(
        update={"stress": {**actor.stress, "weird": StressTrack(track_key="weird", capacity=4, filled=4)}}
    )
    record, _ = evaluate_fallout(actor, "weird", "camp_1")
    assert record.mechanical_hooks.get("dungeon_influence") is True


def test_weird_fallout_has_write_memory_flag() -> None:
    actor = _pc()
    actor = actor.model_copy(
        update={"stress": {**actor.stress, "weird": StressTrack(track_key="weird", capacity=4, filled=4)}}
    )
    record, _ = evaluate_fallout(actor, "weird", "camp_1")
    assert record.mechanical_hooks.get("write_memory") is True
