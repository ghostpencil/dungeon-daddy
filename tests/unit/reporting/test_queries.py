import uuid

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.reporting.queries import (
    action_usage,
    clock_activity,
    fallout_frequency,
    memory_stats,
    outcome_breakdown,
    proposal_stats,
    stress_distribution,
)


def _evt(campaign_id: str, event_type: str, payload: dict) -> DomainEvent:
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        event_type=event_type,
        payload=payload,
    )


def test_action_usage_empty():
    assert action_usage([]) == []


def test_action_usage_tallies_and_sorts_desc():
    events = [
        _evt("c1", "action.resolved", {"action_key": "fight"}),
        _evt("c1", "action.resolved", {"action_key": "fight"}),
        _evt("c1", "action.resolved", {"action_key": "fight"}),
        _evt("c1", "action.resolved", {"action_key": "study"}),
    ]
    rows = action_usage(events)
    assert len(rows) == 2
    assert rows[0].action_key == "fight"
    assert rows[0].count == 3
    assert rows[1].action_key == "study"
    assert rows[1].count == 1


def test_action_usage_ignores_other_event_types():
    events = [
        _evt("c1", "stress.marked", {"action_key": "fight"}),
        _evt("c1", "action.resolved", {"action_key": "move"}),
    ]
    rows = action_usage(events)
    assert len(rows) == 1
    assert rows[0].action_key == "move"


def test_outcome_breakdown_counts_correctly():
    events = [
        _evt("c1", "action.resolved", {"action_key": "fight", "outcome": "partial"}),
        _evt("c1", "action.resolved", {"action_key": "fight", "outcome": "partial"}),
        _evt("c1", "action.resolved", {"action_key": "fight", "outcome": "miss"}),
    ]
    ob = outcome_breakdown(events)
    assert ob.partial == 2
    assert ob.miss == 1
    assert ob.full == 0
    assert ob.critical == 0


def test_outcome_breakdown_empty():
    ob = outcome_breakdown([])
    assert ob.critical == 0
    assert ob.full == 0
    assert ob.partial == 0
    assert ob.miss == 0


def test_stress_distribution_empty():
    assert stress_distribution([]) == []


def test_stress_distribution_groups_and_sums():
    events = [
        _evt("c1", "stress.marked", {"actor_id": "a1", "track_key": "body", "count": 2}),
        _evt("c1", "stress.marked", {"actor_id": "a1", "track_key": "body", "count": 1}),
        _evt("c1", "stress.marked", {"actor_id": "a2", "track_key": "composure", "count": 1}),
    ]
    rows = stress_distribution(events)
    assert len(rows) == 2
    a1_body = next(r for r in rows if r.actor_id == "a1" and r.track_key == "body")
    a2_comp = next(r for r in rows if r.actor_id == "a2" and r.track_key == "composure")
    assert a1_body.total_marks == 3
    assert a2_comp.total_marks == 1


# --- Slice 3: Clock Activity and Fallout ---

def test_clock_activity_empty():
    assert clock_activity([]) == []


def test_clock_activity_counts_advances_and_captures_last_status():
    events = [
        _evt("c1", "clock.advanced", {"clock_id": "clk1", "label": "Bone Warden", "status": "active"}),
        _evt("c1", "clock.advanced", {"clock_id": "clk1", "label": "Bone Warden", "status": "completed"}),
        _evt("c1", "clock.advanced", {"clock_id": "clk2", "label": "Choir Door", "status": "active"}),
    ]
    rows = clock_activity(events)
    assert len(rows) == 2
    clk1 = next(r for r in rows if r.clock_id == "clk1")
    clk2 = next(r for r in rows if r.clock_id == "clk2")
    assert clk1.times_advanced == 2
    assert clk1.final_status == "completed"
    assert clk1.label == "Bone Warden"
    assert clk2.times_advanced == 1
    assert clk2.final_status == "active"


def test_clock_activity_sorted_by_advances_desc():
    events = [
        _evt("c1", "clock.advanced", {"clock_id": "clk2", "label": "B", "status": "active"}),
        _evt("c1", "clock.advanced", {"clock_id": "clk1", "label": "A", "status": "active"}),
        _evt("c1", "clock.advanced", {"clock_id": "clk1", "label": "A", "status": "active"}),
    ]
    rows = clock_activity(events)
    assert rows[0].clock_id == "clk1"


def test_fallout_frequency_empty_when_no_actors(repo):
    rows = fallout_frequency(repo, "camp-none")
    assert rows == []


def test_fallout_frequency_returns_rows_for_actor(repo):
    import uuid

    from dungeon_daddy.rpg.models import FalloutRecord
    campaign_id = "camp-test"
    actor_id = f"actor:{uuid.uuid4()}"
    repo.save_actor(actor_id, campaign_id, "pc", "pc-mara", "Mara")
    fallout = FalloutRecord(
        fallout_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        actor_id=actor_id,
        track_key="body",
        severity="minor",
        title="Bruised",
        summary="Took a hit",
        status="active",
    )
    repo.save_fallout_record(fallout)
    rows = fallout_frequency(repo, campaign_id)
    assert len(rows) == 1
    assert rows[0].actor_id == actor_id
    assert rows[0].track_key == "body"
    assert rows[0].severity == "minor"


# --- Slice 4: Proposal Stats and Memory Stats ---

def test_proposal_stats_empty():
    ps = proposal_stats([])
    assert ps.applied == 0
    assert ps.rejected == 0
    assert ps.by_kind == {}


def test_proposal_stats_counts_applied_and_rejected():
    events = [
        _evt("c1", "proposal.applied", {"kind": "create_memory"}),
        _evt("c1", "proposal.applied", {"kind": "create_memory"}),
        _evt("c1", "proposal.rejected", {"kind": "advance_clock", "reason": "unknown clock"}),
    ]
    ps = proposal_stats(events)
    assert ps.applied == 2
    assert ps.rejected == 1
    assert ps.by_kind == {"create_memory": 2}


def test_memory_stats_counts_events_and_repo(repo):
    events = [
        _evt("c1", "memory_created", {"memory_id": "m1"}),
        _evt("c1", "memory_created", {"memory_id": "m2"}),
    ]
    import uuid
    repo.save_memory_entry(str(uuid.uuid4()), "c1", "event", "Title", "Summary", importance=3)
    ms = memory_stats(events, repo, "c1")
    assert ms.created == 2
    assert ms.draft == 1


def test_fallout_frequency_campaign_isolation(repo):
    import uuid

    from dungeon_daddy.rpg.models import FalloutRecord
    actor_id = f"actor:{uuid.uuid4()}"
    repo.save_actor(actor_id, "camp-a", "pc", "pc-x", "X")
    fallout = FalloutRecord(
        fallout_id=str(uuid.uuid4()),
        campaign_id="camp-a",
        actor_id=actor_id,
        track_key="body",
        severity="minor",
        title="Bruised",
        summary="Took a hit",
        status="active",
    )
    repo.save_fallout_record(fallout)
    rows = fallout_frequency(repo, "camp-b")
    assert rows == []
