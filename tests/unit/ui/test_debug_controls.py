"""Unit tests for DebugControls — Phase 30 step 30-6."""
from __future__ import annotations

from unittest.mock import MagicMock

from dungeon_daddy.rpg.models import (
    ActionRequest,
    ClockState,
    ReactionClockLine,
    ReactionStressLine,
    StressTrack,
    WorldReaction,
)
from dungeon_daddy.rpg.service import RpgService


def _controls(sync_reporter=None):
    from dungeon_daddy.ui.panels.debug_controls import DebugControls
    return DebugControls(rpg_service=RpgService(), sync_reporter=sync_reporter)


def _request() -> ActionRequest:
    return ActionRequest(
        campaign_id="c1",
        actor_id="a1",
        action_key="hunt",
        dice_pool=2,
    )


def _track() -> StressTrack:
    return StressTrack(track_key="body", capacity=6, filled=0)


def _clock() -> ClockState:
    return ClockState(
        clock_id="ck1",
        campaign_id="c1",
        label="Patrol",
        segments=6,
        filled=1,
    )


# ---------------------------------------------------------------------------
# Bullet 1 — resolve_sample_action calls rpg_service and stores outcome
# ---------------------------------------------------------------------------

def test_resolve_sample_action_returns_resolution():
    ctrl = _controls()
    resolution = ctrl.resolve_sample_action(_request(), fixed=[5, 5])
    assert resolution.outcome in {"critical", "full", "partial", "miss"}


def test_resolve_sample_action_stores_last_resolution():
    ctrl = _controls()
    ctrl.resolve_sample_action(_request(), fixed=[5, 5])
    assert ctrl._last_resolution is not None
    assert ctrl._last_resolution.action_key == "hunt"


# ---------------------------------------------------------------------------
# Bullet 2 — apply_stress calls rpg_service and stores result
# ---------------------------------------------------------------------------

def test_apply_stress_updates_track():
    ctrl = _controls()
    updated = ctrl.apply_stress(actor_id="a1", campaign_id="c1", track=_track(), amount=2)
    assert updated.filled == 2


def test_apply_stress_stores_last_track():
    ctrl = _controls()
    ctrl.apply_stress(actor_id="a1", campaign_id="c1", track=_track(), amount=1)
    assert ctrl._last_stress_track is not None
    assert ctrl._last_stress_track.filled == 1


# ---------------------------------------------------------------------------
# Bullet 3 — advance_clock calls rpg_service and stores result
# ---------------------------------------------------------------------------

def test_advance_clock_increments_filled():
    ctrl = _controls()
    updated = ctrl.advance_clock(clock=_clock(), ticks=2)
    assert updated.filled == 3


def test_advance_clock_stores_last_clock():
    ctrl = _controls()
    ctrl.advance_clock(clock=_clock(), ticks=1)
    assert ctrl._last_clock is not None
    assert ctrl._last_clock.filled == 2


# ---------------------------------------------------------------------------
# Bullet 4 — generate_sync_report calls sync_reporter.check()
# ---------------------------------------------------------------------------

def test_generate_sync_report_calls_check():
    mock_reporter = MagicMock()
    mock_reporter.check.return_value = []
    ctrl = _controls(sync_reporter=mock_reporter)
    issues = ctrl.generate_sync_report()
    mock_reporter.check.assert_called_once()
    assert issues == []


def test_generate_sync_report_stores_issues():
    from dungeon_daddy.memory.sync import SyncIssue
    mock_reporter = MagicMock()
    issue = SyncIssue(kind="missing_file", memory_id="m1", path="rpg-memory/npc/x.md")
    mock_reporter.check.return_value = [issue]
    ctrl = _controls(sync_reporter=mock_reporter)
    ctrl.generate_sync_report()
    assert ctrl._last_sync_issues is not None
    assert len(ctrl._last_sync_issues) == 1
    assert ctrl._last_sync_issues[0].kind == "missing_file"


def test_generate_sync_report_no_reporter_returns_empty():
    ctrl = _controls(sync_reporter=None)
    issues = ctrl.generate_sync_report()
    assert issues == []


# ---------------------------------------------------------------------------
# Bullet 5 — create_test_memory_note creates a MemoryEntry
# ---------------------------------------------------------------------------

def test_create_test_memory_note_returns_entry():
    from dungeon_daddy.memory.models import MemoryEntry
    ctrl = _controls()
    entry = ctrl.create_test_memory_note(campaign_id="c1", title="Test Note")
    assert isinstance(entry, MemoryEntry)
    assert entry.title == "Test Note"
    assert entry.campaign_id == "c1"


def test_create_test_memory_note_stores_entry():
    ctrl = _controls()
    ctrl.create_test_memory_note(campaign_id="c1", title="Test Note")
    assert ctrl._last_memory_note is not None
    assert ctrl._last_memory_note.title == "Test Note"


# ---------------------------------------------------------------------------
# Bullet 1 — set_bundle stores the bundle as _last_bundle
# ---------------------------------------------------------------------------

def _bundle(**kwargs):
    from dungeon_daddy.memory.models import ContextBundle
    defaults = dict(bundle_id="b1", campaign_id="c1", mode="run_scene")
    defaults.update(kwargs)
    return ContextBundle(**defaults)


def test_set_bundle_stores_last_bundle():
    ctrl = _controls()
    b = _bundle()
    ctrl.set_bundle(b)
    assert ctrl._last_bundle is b


# ---------------------------------------------------------------------------
# Bullet 2 — bundle_section_lines includes bundle_id, card count, trimmed count
# ---------------------------------------------------------------------------

def test_bundle_section_lines_shows_bundle_id_and_counts():
    ctrl = _controls()
    b = _bundle(
        bundle_id="bbb-123",
        memory_cards=[
            {"memory_id": "m1", "title": "T1", "summary": "", "importance": 5},
            {"memory_id": "m2", "title": "T2", "summary": "", "importance": 9},
        ],
        must_remember=["m2"],
        provenance={"retrieved": 5, "omitted": 3, "focus_actor_ids": []},
    )
    ctrl.set_bundle(b)
    lines = ctrl.bundle_section_lines()
    text = "\n".join(lines)
    assert "bbb-123" in text
    assert "2" in text   # card count
    assert "3" in text   # omitted / trimmed count


# ---------------------------------------------------------------------------
# Bullet 3 — each card listed with title and reason (importance vs retrieved)
# ---------------------------------------------------------------------------

def test_bundle_section_lines_shows_card_title_and_reason():
    ctrl = _controls()
    b = _bundle(
        memory_cards=[
            {"memory_id": "m1", "title": "Dragon Sighting", "summary": "", "importance": 5},
            {"memory_id": "m2", "title": "King's Promise", "summary": "", "importance": 9},
        ],
        must_remember=["m2"],
        provenance={"retrieved": 2, "omitted": 0, "focus_actor_ids": []},
    )
    ctrl.set_bundle(b)
    lines = ctrl.bundle_section_lines()
    text = "\n".join(lines)
    assert "Dragon Sighting" in text
    assert "retrieved" in text
    assert "King's Promise" in text
    assert "importance" in text


# ---------------------------------------------------------------------------
# Slice A6 (T7) — bundle_section_lines surfaces the pre-fetched Related Lore so
# it can be GUI-verified in the debug panel.
# ---------------------------------------------------------------------------

def test_bundle_section_lines_shows_related_lore():
    ctrl = _controls()
    b = _bundle(
        related_lore=[
            {"memory_id": "L1", "title": "The Old Pact", "summary": "", "importance": 5},
        ],
        provenance={"retrieved": 0, "omitted": 0, "focus_actor_ids": [],
                    "related_lore_retrieved": 1, "related_lore_omitted": 0,
                    "related_lore_anchor_tags": ["thread:pact"]},
    )
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.bundle_section_lines())
    assert "Related Lore" in text
    assert "The Old Pact" in text


def test_bundle_section_lines_omits_related_lore_when_empty():
    ctrl = _controls()
    b = _bundle()  # no related lore
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.bundle_section_lines())
    assert "Related Lore" not in text


# ---------------------------------------------------------------------------
# Bullet 4 — no bundle → "No bundle built yet"
# ---------------------------------------------------------------------------

def test_bundle_section_lines_no_bundle():
    ctrl = _controls()
    lines = ctrl.bundle_section_lines()
    assert any("No bundle built yet" in line for line in lines)


# ---------------------------------------------------------------------------
# Slice B4e — set_lookups / lookup_section_lines (narrator lookup provenance)
# ---------------------------------------------------------------------------

def _lookup_record(**kwargs):
    from dungeon_daddy.llm.lookup_tool import LookupRecord
    return LookupRecord(**kwargs)


def test_set_lookups_stores_records():
    ctrl = _controls()
    recs = [_lookup_record(query="mira")]
    ctrl.set_lookups(recs)
    assert ctrl._last_lookups is recs


def test_lookup_section_lines_shows_count_query_and_hits():
    ctrl = _controls()
    ctrl.set_lookups([
        _lookup_record(query="mira", hit_count=3),
        _lookup_record(query="vault", hit_count=1),
    ])
    text = "\n".join(ctrl.lookup_section_lines())
    assert "World lookups: 2" in text
    assert "mira" in text
    assert "3 hit(s)" in text


def test_lookup_section_lines_shows_tags_when_no_query():
    ctrl = _controls()
    ctrl.set_lookups([_lookup_record(query=None, tags=["theme:guilt"], hit_count=2)])
    text = "\n".join(ctrl.lookup_section_lines())
    assert "theme:guilt" in text


def test_lookup_section_lines_shows_redirect_flag():
    ctrl = _controls()
    ctrl.set_lookups([
        _lookup_record(query="mira", hit_count=2, overlap_count=2, redirected=True),
    ])
    text = "\n".join(ctrl.lookup_section_lines())
    assert "REDIRECT" in text


def test_lookup_section_lines_shows_redundant_overlap():
    ctrl = _controls()
    ctrl.set_lookups([
        _lookup_record(query="mira", hit_count=3, overlap_count=1),
    ])
    text = "\n".join(ctrl.lookup_section_lines())
    assert "redundant 1/3" in text


def test_lookup_section_lines_no_lookups():
    ctrl = _controls()
    assert any("No lookups yet" in line for line in ctrl.lookup_section_lines())


# ---------------------------------------------------------------------------
# Bullet — set_reaction / reaction_section_lines
# ---------------------------------------------------------------------------

def _world_reaction(outcome: str = "miss") -> WorldReaction:
    clock_line = ReactionClockLine(
        clock_id="ck1", label="Heat Rising", ticks=2,
        new_filled=3, new_status="active", reason="miss",
    )
    stress_line = ReactionStressLine(
        actor_id="a1", display_name="Hero", track_key="body",
        amount=2, new_filled=2, reason="miss consequence",
    )
    return WorldReaction(
        reaction_id="r1",
        campaign_id="c1",
        source_resolution_id="res1",
        outcome=outcome,  # type: ignore[arg-type]
        clock_lines=[clock_line],
        stress_lines=[stress_line],
        summary_lines=["World reaction (MISS):", "  Clock [Heat Rising]: 1→3 (+2)"],
    )


def test_set_reaction_stores_last_reaction():
    ctrl = _controls()
    wr = _world_reaction()
    ctrl.set_reaction(wr)
    assert ctrl._last_reaction is wr


def test_reaction_section_lines_no_reaction():
    ctrl = _controls()
    lines = ctrl.reaction_section_lines()
    assert any("No reaction" in line for line in lines)


def test_reaction_section_lines_shows_summary():
    ctrl = _controls()
    ctrl.set_reaction(_world_reaction("miss"))
    lines = ctrl.reaction_section_lines()
    text = "\n".join(lines)
    assert "MISS" in text or "miss" in text.lower()
    assert "Heat Rising" in text


# ---------------------------------------------------------------------------
# clock_section_lines — shows clock labels from the active bundle
# ---------------------------------------------------------------------------

def test_clock_section_lines_shows_clock_labels():
    ctrl = _controls()
    b = _bundle(
        open_clocks=[
            {"clock_id": "ck1", "label": "The Forge Awakens", "filled": 2, "segments": 6, "status": "active"},
            {"clock_id": "ck2", "label": "Party Detected", "filled": 1, "segments": 4, "status": "active"},
        ],
    )
    ctrl.set_bundle(b)
    lines = ctrl.clock_section_lines()
    text = "\n".join(lines)
    assert "The Forge Awakens" in text
    assert "Party Detected" in text


def test_clock_section_lines_no_bundle():
    ctrl = _controls()
    lines = ctrl.clock_section_lines()
    assert any("No bundle" in line for line in lines)


def test_clock_section_lines_filled_and_segments_shown():
    ctrl = _controls()
    b = _bundle(
        open_clocks=[
            {"clock_id": "ck1", "label": "Alarm", "filled": 3, "segments": 6, "status": "active"},
        ],
    )
    ctrl.set_bundle(b)
    lines = ctrl.clock_section_lines()
    text = "\n".join(lines)
    assert "3" in text
    assert "6" in text


# ---------------------------------------------------------------------------
# clock_section_lines — Phase 35.5 level/scope metadata
# ---------------------------------------------------------------------------

def _clock_dict(**kwargs) -> dict:
    defaults = {
        "clock_id": "ck1", "label": "Test Clock", "filled": 1,
        "segments": 6, "status": "active", "clock_level": "dungeon",
        "category": None, "scope_room_id": None, "action_tags": [],
        "level_id": None, "owner_actor_id": None,
        "stakes": None, "completion_effect": None, "visible_to_player": True,
    }
    defaults.update(kwargs)
    return defaults


def test_clock_section_lines_shows_clock_level():
    ctrl = _controls()
    b = _bundle(open_clocks=[_clock_dict(clock_level="quest")])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "quest" in text


def test_clock_section_lines_shows_category():
    ctrl = _controls()
    b = _bundle(open_clocks=[_clock_dict(category="danger")])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "danger" in text


def test_clock_section_lines_room_clock_shows_scope_room_id():
    ctrl = _controls()
    b = _bundle(open_clocks=[_clock_dict(clock_level="room", scope_room_id="boiler_room")])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "room:boiler_room" in text


def test_clock_section_lines_level_clock_shows_level_id():
    ctrl = _controls()
    b = _bundle(open_clocks=[_clock_dict(clock_level="level", level_id="level_2")])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "level:level_2" in text


def test_clock_section_lines_shows_action_tags():
    ctrl = _controls()
    b = _bundle(open_clocks=[_clock_dict(action_tags=["move", "tinker"])])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "actions:" in text
    assert "move" in text
    assert "tinker" in text


def test_clock_section_lines_no_action_tags_omits_actions_label():
    ctrl = _controls()
    b = _bundle(open_clocks=[_clock_dict(action_tags=[])])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "actions:" not in text


def test_clock_section_lines_minimal_clock_still_renders():
    ctrl = _controls()
    b = _bundle(open_clocks=[
        {"clock_id": "ck1", "label": "Old Clock", "filled": 0, "segments": 4, "status": "active"},
    ])
    ctrl.set_bundle(b)
    lines = ctrl.clock_section_lines()
    text = "\n".join(lines)
    assert "Old Clock" in text
    assert "[0/4]" in text


def test_clock_section_lines_character_clock_shows_display_name():
    ctrl = _controls()
    b = _bundle(open_clocks=[
        _clock_dict(
            clock_level="character",
            owner_actor_id="some-uuid-1234",
            owner_display_name="Mira Coldwell",
        ),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "character:Mira Coldwell" in text
    assert "some-uuid-1234" not in text


def test_clock_section_lines_faction_clock_shows_display_name():
    ctrl = _controls()
    b = _bundle(open_clocks=[
        _clock_dict(
            clock_level="faction",
            owner_actor_id="some-uuid-5678",
            owner_display_name="The Desert Djinn",
        ),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "faction:The Desert Djinn" in text
    assert "some-uuid-5678" not in text


def test_clock_section_lines_character_clock_falls_back_to_id_when_no_display_name():
    ctrl = _controls()
    b = _bundle(open_clocks=[
        _clock_dict(
            clock_level="character",
            owner_actor_id="fallback-id",
        ),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "character:fallback-id" in text


# ---------------------------------------------------------------------------
# Level-scoped clock filtering
# ---------------------------------------------------------------------------

def test_clock_section_hides_level_clock_from_other_level():
    ctrl = _controls()
    ctrl.set_current_level_id("level-1")
    b = _bundle(open_clocks=[
        _clock_dict(clock_level="level", level_id="level-2"),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "level-2" not in text


def test_clock_section_shows_level_clock_matching_current_level():
    ctrl = _controls()
    ctrl.set_current_level_id("level-1")
    b = _bundle(open_clocks=[
        _clock_dict(clock_level="level", level_id="level-1"),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "level-1" in text


def test_clock_section_non_level_clocks_unaffected_by_level_filter():
    ctrl = _controls()
    ctrl.set_current_level_id("level-1")
    b = _bundle(open_clocks=[
        _clock_dict(clock_level="dungeon"),
        _clock_dict(clock_level="room", scope_room_id="chapel"),
    ])
    ctrl.set_bundle(b)
    lines = ctrl.clock_section_lines()
    assert any("chapel" in line for line in lines)
    assert "Clocks: 2 active" in lines[0]


# ---------------------------------------------------------------------------
# Room-scoped clock filtering
# ---------------------------------------------------------------------------

def test_clock_section_hides_room_clock_from_other_level():
    ctrl = _controls()
    ctrl.set_current_level_room_ids({"R1", "R2"})
    b = _bundle(open_clocks=[
        _clock_dict(clock_level="room", scope_room_id="R3"),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "R3" not in text


def test_clock_section_shows_room_clock_on_current_level():
    ctrl = _controls()
    ctrl.set_current_level_room_ids({"R1", "R2"})
    b = _bundle(open_clocks=[
        _clock_dict(clock_level="room", scope_room_id="R1"),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "R1" in text


def test_clock_section_room_clock_unfiltered_when_room_ids_unknown():
    ctrl = _controls()
    # no set_current_level_room_ids call — room_ids empty, filter disabled
    b = _bundle(open_clocks=[
        _clock_dict(clock_level="room", scope_room_id="R9"),
    ])
    ctrl.set_bundle(b)
    text = "\n".join(ctrl.clock_section_lines())
    assert "R9" in text


# ---------------------------------------------------------------------------
# Slice 8 — proposal_section_lines provenance display
# ---------------------------------------------------------------------------

def _validation_result(**kwargs):
    from dungeon_daddy.rpg.proposal_validator import ValidationResult
    defaults = dict(source="llm_draft")
    defaults.update(kwargs)
    return ValidationResult(**defaults)


def _apply_result(**kwargs):
    from dungeon_daddy.rpg.proposal_applier import ApplyResult
    defaults: dict = {}
    defaults.update(kwargs)
    return ApplyResult(**defaults)


def test_proposal_section_lines_no_proposal():
    ctrl = _controls()
    lines = ctrl.proposal_section_lines()
    assert any("No proposal" in line for line in lines)


def test_proposal_section_lines_shows_source_label():
    ctrl = _controls()
    ctrl.set_proposal_result(_validation_result(source="llm_draft"))
    text = "\n".join(ctrl.proposal_section_lines())
    assert "llm_draft" in text


def test_proposal_section_lines_shows_accepted_count():
    from dungeon_daddy.rpg.proposal import CreateMemoryChange
    change = CreateMemoryChange(title="Gate opened", summary="s", importance=5, tags=[])
    ctrl = _controls()
    ctrl.set_proposal_result(_validation_result(accepted=[change]))
    text = "\n".join(ctrl.proposal_section_lines())
    assert "Accepted: 1" in text


def test_proposal_section_lines_shows_rejected_reason():
    from dungeon_daddy.rpg.proposal import AdvanceClockChange
    from dungeon_daddy.rpg.proposal_validator import RejectedChange
    change = AdvanceClockChange(clock_id="ghost_clock", amount=1, reason="spooky")
    rejected = RejectedChange(change=change, reason="Unknown clock reference: ghost_clock")
    ctrl = _controls()
    ctrl.set_proposal_result(_validation_result(rejected=[rejected]))
    text = "\n".join(ctrl.proposal_section_lines())
    assert "Unknown clock reference: ghost_clock" in text


def test_proposal_section_lines_shows_applied_count():
    from dungeon_daddy.rpg.proposal import CreateMemoryChange
    change = CreateMemoryChange(title="Gate opened", summary="s", importance=5, tags=[])
    ctrl = _controls()
    ctrl.set_proposal_result(
        _validation_result(accepted=[change]),
        _apply_result(applied=[change]),
    )
    text = "\n".join(ctrl.proposal_section_lines())
    assert "Applied: 1" in text


def test_proposal_section_lines_shows_skipped_count():
    from dungeon_daddy.rpg.proposal import ApplyConsequenceChange
    change = ApplyConsequenceChange(
        actor_id="actor_mara", track_key="body", amount=1, reason="dup"
    )
    ctrl = _controls()
    ctrl.set_proposal_result(
        _validation_result(),
        _apply_result(skipped=[change]),
    )
    text = "\n".join(ctrl.proposal_section_lines())
    assert "Skipped: 1" in text


def test_proposal_section_lines_shows_skipped_kind():
    from dungeon_daddy.rpg.proposal import ApplyConsequenceChange
    change = ApplyConsequenceChange(
        actor_id="actor_mara", track_key="body", amount=1, reason="dup"
    )
    ctrl = _controls()
    ctrl.set_proposal_result(
        _validation_result(),
        _apply_result(skipped=[change]),
    )
    text = "\n".join(ctrl.proposal_section_lines())
    assert "[SKIPPED]" in text
    assert "apply_consequence" in text


# ---------------------------------------------------------------------------
# Phase 37.1.5 — last_action_section_lines
# ---------------------------------------------------------------------------

def test_last_action_section_lines_no_resolution():
    ctrl = _controls()
    lines = ctrl.last_action_section_lines()
    assert any("No action" in line for line in lines)


def test_last_action_section_lines_shows_actor_and_action():
    ctrl = _controls()
    ctrl.resolve_sample_action(
        ActionRequest(campaign_id="c1", actor_id="hero", action_key="hunt", dice_pool=2),
        fixed=[5, 5],
    )
    text = "\n".join(ctrl.last_action_section_lines())
    assert "hero" in text
    assert "hunt" in text


def test_last_action_section_lines_shows_intent():
    ctrl = _controls()
    ctrl.resolve_sample_action(
        ActionRequest(campaign_id="c1", actor_id="a1", action_key="study", dice_pool=1, intent="ritual"),
        fixed=[6],
    )
    text = "\n".join(ctrl.last_action_section_lines())
    assert "ritual" in text


def test_last_action_section_lines_shows_none_when_no_intent():
    ctrl = _controls()
    ctrl.resolve_sample_action(
        ActionRequest(campaign_id="c1", actor_id="a1", action_key="hunt", dice_pool=1),
        fixed=[3],
    )
    text = "\n".join(ctrl.last_action_section_lines())
    assert "(none)" in text


def test_last_action_section_lines_shows_dice_and_outcome():
    ctrl = _controls()
    ctrl.resolve_sample_action(
        ActionRequest(campaign_id="c1", actor_id="a1", action_key="hunt", dice_pool=2),
        fixed=[6, 6],
    )
    text = "\n".join(ctrl.last_action_section_lines())
    assert "6" in text
    assert "critical" in text


# ---------------------------------------------------------------------------
# Phase 37.1.5 — reaction_section_lines structured deterministic output
# ---------------------------------------------------------------------------

def test_reaction_section_lines_shows_deterministic_header():
    ctrl = _controls()
    ctrl.set_reaction(_world_reaction("miss"))
    text = "\n".join(ctrl.reaction_section_lines())
    assert "eterministic" in text  # "Deterministic" header present


def test_reaction_section_lines_shows_clock_line_detail():
    ctrl = _controls()
    ctrl.set_reaction(_world_reaction("miss"))
    text = "\n".join(ctrl.reaction_section_lines())
    assert "Heat Rising" in text
    assert "+2" in text


def test_reaction_section_lines_shows_stress_line_detail():
    ctrl = _controls()
    ctrl.set_reaction(_world_reaction("miss"))
    text = "\n".join(ctrl.reaction_section_lines())
    assert "body" in text
    assert "Hero" in text


def test_reaction_section_lines_shows_fallout_when_triggered():
    from dungeon_daddy.rpg.models import ReactionStressLine, WorldReaction
    stress_line = ReactionStressLine(
        actor_id="a1", display_name="Hero", track_key="composure",
        amount=3, new_filled=6, triggered_fallout=True, reason="severe hit",
    )
    wr = WorldReaction(
        reaction_id="r2", campaign_id="c1", source_resolution_id="res2",
        outcome="miss", stress_lines=[stress_line],
    )
    ctrl = _controls()
    ctrl.set_reaction(wr)
    text = "\n".join(ctrl.reaction_section_lines())
    assert "FALLOUT" in text.upper()


def test_reaction_section_lines_no_clocks_no_stress_shows_nothing_changed():
    from dungeon_daddy.rpg.models import WorldReaction
    wr = WorldReaction(
        reaction_id="r3", campaign_id="c1", source_resolution_id="res3",
        outcome="full",
    )
    ctrl = _controls()
    ctrl.set_reaction(wr)
    text = "\n".join(ctrl.reaction_section_lines())
    assert "(nothing changed)" in text


# ---------------------------------------------------------------------------
# Phase 37.1.5 — proposal parse_status display
# ---------------------------------------------------------------------------

def test_proposal_section_lines_shows_parse_status_when_present():
    ctrl = _controls()
    ctrl.set_proposal_result(_validation_result(parse_status="ok"))
    text = "\n".join(ctrl.proposal_section_lines())
    assert "ok" in text


def test_proposal_section_lines_omits_parse_status_when_none():
    ctrl = _controls()
    ctrl.set_proposal_result(_validation_result())
    text = "\n".join(ctrl.proposal_section_lines())
    assert "parse_status" not in text
