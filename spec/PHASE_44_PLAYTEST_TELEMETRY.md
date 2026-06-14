# Phase 44 — Playtest Telemetry and Balance Reports

## Goal

Generate human-readable balance reports from domain events and DuckDB tables.
No new UI panel. Output is a formatted text report (CLI tool + Python API).

## Reports Covered

- Most-used actions (tallied from `action.resolved` events)
- Outcome breakdown (critical / full / partial / miss)
- Stress distribution (marks per actor per track, from `stress.marked`)
- Clock activity (advance count + final status, from `clock.advanced`)
- Fallout frequency (count per actor per track, from `fallout` table)
- Proposal acceptance / rejection rates (new `proposal.applied` and `proposal.rejected` events)
- Memory lifecycle (created / approved / rejected / draft, from `memory_entries` + `memory_created` events)

---

## New Domain Events

Two events must be added; neither exists today.

### `proposal.applied`
Emitted in `dungeon_daddy/rpg/proposal_applier.py` once per change that is
actually applied (not skipped).

Payload: `{"kind": "<change.kind>", "reason": "<optional reason text>"}`

### `proposal.rejected`
Emitted logically by `dungeon_daddy/rpg/proposal_validator.py`; because the
validator is a pure function with no repo dependency, `ValidationResult` gains a
new field:

```python
rejection_events: list[DomainEvent] = field(default_factory=list)
```

The call site (play view / world reaction service) is responsible for inserting
these events into the repo after validation. This keeps the validator pure.

---

## New Module: `dungeon_daddy/reporting/`

```
dungeon_daddy/reporting/
    __init__.py
    models.py       # Pydantic models for each sub-report
    queries.py      # Pure aggregation functions over list[DomainEvent] + repo calls
    reporter.py     # build_report(repo, campaign_id) -> PlaytestReport

tests/unit/reporting/
    __init__.py
    conftest.py     # repo fixture (same pattern as tests/unit/memory/conftest.py)
    test_models.py
    test_queries.py
    test_reporter.py

tools/playtest_report.py   # CLI: prints formatted report for a given campaign
```

### Pydantic Models (`models.py`)

```python
class ActionUsageRow(BaseModel):
    action_key: str
    count: int

class OutcomeBreakdown(BaseModel):
    critical: int = 0
    full: int = 0
    partial: int = 0
    miss: int = 0

class StressDistributionRow(BaseModel):
    actor_id: str
    track_key: str
    total_marks: int

class ClockActivityRow(BaseModel):
    label: str
    clock_id: str
    times_advanced: int
    final_status: str   # taken from the last clock.advanced payload for this clock_id

class FalloutRow(BaseModel):
    actor_id: str
    track_key: str
    severity: str

class ProposalStats(BaseModel):
    applied: int = 0
    rejected: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)

class MemoryStats(BaseModel):
    created: int = 0        # count of memory_created events
    approved: int = 0       # from repo.count_by_status()
    rejected: int = 0
    draft: int = 0
    archived: int = 0

class PlaytestReport(BaseModel):
    campaign_id: str
    generated_at: datetime
    action_usage: list[ActionUsageRow]
    outcome_breakdown: OutcomeBreakdown
    stress_distribution: list[StressDistributionRow]
    clock_activity: list[ClockActivityRow]
    fallout_frequency: list[FalloutRow]
    proposal_stats: ProposalStats
    memory_stats: MemoryStats
```

### Aggregation Strategy

All query functions accept `list[DomainEvent]` (already fetched with parsed payload
dicts). Only `fallout_frequency` and `memory_stats` need an extra repo call.
`repo.get_domain_events(campaign_id)` is called once in `reporter.py` and shared.

```python
def action_usage(events: list[DomainEvent]) -> list[ActionUsageRow]:
    # filter event_type == "action.resolved", tally payload["action_key"], sort desc

def outcome_breakdown(events: list[DomainEvent]) -> OutcomeBreakdown:
    # filter event_type == "action.resolved", tally payload["outcome"]

def stress_distribution(events: list[DomainEvent]) -> list[StressDistributionRow]:
    # filter event_type == "stress.marked", group by (actor_id, track_key), sum count

def clock_activity(events: list[DomainEvent]) -> list[ClockActivityRow]:
    # filter event_type == "clock.advanced", group by payload["clock_id"]
    # last event provides label and final_status; sort by times_advanced desc

def fallout_frequency(repo: MemoryRepository, campaign_id: str) -> list[FalloutRow]:
    # get_actors_by_campaign(campaign_id) → actor_ids
    # for each actor: get_fallout_records(campaign_id, actor_id) → flatten

def proposal_stats(events: list[DomainEvent]) -> ProposalStats:
    # tally "proposal.applied" and "proposal.rejected" events, group by payload["kind"]

def memory_stats(
    events: list[DomainEvent], repo: MemoryRepository, campaign_id: str
) -> MemoryStats:
    # created = count "memory_created" events
    # approved/rejected/draft/archived from repo.count_by_status(campaign_id)
```

### `build_report` (`reporter.py`)

```python
def build_report(repo: MemoryRepository, campaign_id: str) -> PlaytestReport:
    events = repo.get_domain_events(campaign_id)
    return PlaytestReport(
        campaign_id=campaign_id,
        generated_at=datetime.now(timezone.utc),
        action_usage=action_usage(events),
        outcome_breakdown=outcome_breakdown(events),
        stress_distribution=stress_distribution(events),
        clock_activity=clock_activity(events),
        fallout_frequency=fallout_frequency(repo, campaign_id),
        proposal_stats=proposal_stats(events),
        memory_stats=memory_stats(events, repo, campaign_id),
    )
```

### CLI Tool (`tools/playtest_report.py`)

Usage: `python tools/playtest_report.py <db_path> <campaign_id>`

Example output:
```
=== Playtest Balance Report: camp:the-crucible ===
Generated: 2026-06-13T...

--- Action Usage ---
fight       12
study        7

--- Outcome Breakdown ---
critical  2   full  5   partial  4   miss  3

--- Stress Distribution ---
pc-mara / body        5 marks
pc-mara / composure   2 marks

--- Clock Activity ---
"Bone Warden Stirs"   4 advances  [completed]
"Choir Door Opening"  2 advances  [active]

--- Fallout Frequency ---
pc-mara / body  minor

--- Proposal Stats ---
Applied: 8   Rejected: 3
  create_memory: applied=6  rejected=1
  adjust_reputation: applied=2  rejected=0
  advance_clock: applied=0  rejected=2

--- Memory Stats ---
Created (events): 6
draft=3  approved=2  rejected=1  archived=0
```

---

## TDD Slices

### Slice 1 — Pydantic Models

**Files created:**
- `dungeon_daddy/reporting/__init__.py`
- `dungeon_daddy/reporting/models.py`
- `tests/unit/reporting/__init__.py`
- `tests/unit/reporting/test_models.py`

**Acceptance criteria:**
- All model classes import cleanly
- `PlaytestReport` validates with all sub-models present and correct types
- Defaults work: `OutcomeBreakdown()` → all-zero fields; `ProposalStats().by_kind == {}`
- `ActionUsageRow` rejects missing `action_key`

---

### Slice 2 — Action and Stress Queries

**Files created/modified:**
- `dungeon_daddy/reporting/queries.py` (`action_usage`, `outcome_breakdown`, `stress_distribution`)
- `tests/unit/reporting/conftest.py` (repo fixture — mirrors `tests/unit/memory/conftest.py`)
- `tests/unit/reporting/test_queries.py`

**Acceptance criteria:**
- `action_usage([])` returns `[]`
- 3 `fight` events + 1 `study` event → two rows, sorted by count desc
- `outcome_breakdown` with 2 partial + 1 miss → `partial=2, miss=1, full=0, critical=0`
- `stress_distribution([])` returns `[]`
- 3 body marks on `a1` + 1 composure mark on `a2` → two rows with correct totals

---

### Slice 3 — Clock Activity and Fallout Queries

**Files modified:**
- `dungeon_daddy/reporting/queries.py` (`clock_activity`, `fallout_frequency`)
- `tests/unit/reporting/test_queries.py`

**Acceptance criteria:**
- `clock_activity([])` returns `[]`
- 2 advances for `clk1` + 1 for `clk2` → two rows; `clk1.times_advanced == 2`
- `final_status` reflects the last event's payload for that `clock_id`
- `fallout_frequency(repo, "camp1")` returns `[]` when no actors exist
- Actor + fallout record → one `FalloutRow` with correct fields
- Campaign isolation verified for both functions

---

### Slice 4 — Proposal Events + Proposal/Memory Stats Queries

**Files modified:**
- `dungeon_daddy/rpg/proposal_validator.py` — add `rejection_events: list[DomainEvent]` to `ValidationResult`; populate per rejected change
- `dungeon_daddy/rpg/proposal_applier.py` — emit `proposal.applied` per applied change
- `dungeon_daddy/reporting/queries.py` (`proposal_stats`, `memory_stats`)
- `tests/unit/rpg/test_proposal_validator.py`
- `tests/unit/rpg/test_proposal_applier.py`
- `tests/unit/reporting/test_queries.py`

**Acceptance criteria:**
- `validate_proposal` with one rejected change → `result.rejection_events` has 1 event, type `"proposal.rejected"`, payload has `kind` and `reason`
- `validate_proposal` with all accepted → `result.rejection_events == []`
- `apply_low_risk_proposals` with `CreateMemoryChange` → repo contains `"proposal.applied"` event
- `apply_low_risk_proposals` with `AdjustReputationChange` → event with `kind="adjust_reputation"`
- `proposal_stats` with 2 applied + 1 rejected → `applied=2, rejected=1, by_kind` correct
- `memory_stats` with events + repo entries → all counters correct

**Call-site wiring note:** wherever `validate_proposal` is called (play view or world
reaction service), insert `result.rejection_events` into the repo after validation.

---

### Slice 5 — `build_report` Integration

**Files created:**
- `dungeon_daddy/reporting/reporter.py`
- `tests/unit/reporting/test_reporter.py`

**Acceptance criteria:**
- `build_report(repo, "camp1")` on empty campaign → valid `PlaytestReport`, all lists `[]`, counters `0`
- Insert one of each event type → all sub-reports have exactly one entry or count of 1
- Campaign isolation: `camp2` events do not appear in `build_report(repo, "camp1")`
- Return type is `PlaytestReport`; `generated_at` is a `datetime`

---

### Slice 6 — CLI Tool

**Files created:**
- `tools/playtest_report.py`
- `tests/unit/tools/test_playtest_report.py`

**Acceptance criteria:**
- `format_report(report)` (pure function) returns a non-empty string containing the campaign_id
- Each section heading present: "Action Usage", "Outcome Breakdown", "Stress Distribution", "Clock Activity", "Fallout Frequency", "Proposal Stats", "Memory Stats"
- `format_report` on a zero-data report does not raise
- `main(["<db_path>", "<campaign_id>"])` callable directly in tests (no subprocess)

---

## Exit Criteria

- All 6 slices complete
- Full test suite passes (no regressions)
- `python tools/playtest_report.py <db_path> <campaign_id>` runs against The Crucible without error
- Report output contains at least one non-zero counter for each section

## Risks

- **`fallout_frequency` requires actor enumeration**: call `repo.get_actors_by_campaign(campaign_id)` first; no new repo method needed.
- **`proposal.rejected` write site**: the call site must insert `result.rejection_events` into the repo after `validate_proposal`. Verify wiring in Slice 4.
- **Clock label drift**: `clock_activity` uses the label from the *last* `clock.advanced` event for a given `clock_id`. If a clock is renamed mid-session, the report shows the most recent name. This is intentional.
