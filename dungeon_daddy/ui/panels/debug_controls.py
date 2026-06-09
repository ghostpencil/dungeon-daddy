"""Debug controls — collapsible section in Play Mode for testing RPG/memory systems."""
from __future__ import annotations

import uuid

from dungeon_daddy.memory.models import ContextBundle, MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActionRequest, ActionResolution, ClockState, StressTrack, WorldReaction
from dungeon_daddy.rpg.service import RpgService


class DebugControls:
    def __init__(
        self,
        rpg_service: RpgService,
        sync_reporter=None,
        mem_repo: MemoryRepository | None = None,
    ) -> None:
        self._rpg = rpg_service
        self._sync_reporter = sync_reporter
        self._mem_repo = mem_repo
        self._last_resolution: ActionResolution | None = None
        self._last_stress_track: StressTrack | None = None
        self._last_clock: ClockState | None = None
        self._last_sync_issues: list | None = None
        self._last_memory_note: MemoryEntry | None = None
        self._last_bundle: ContextBundle | None = None
        self._last_reaction: WorldReaction | None = None
        self._last_validation = None
        self._last_apply_result = None
        self._current_level_id: str | None = None
        self._current_level_room_ids: set[str] = set()

    def last_action_section_lines(self) -> list[str]:
        if self._last_resolution is None:
            return ["No action yet"]
        r = self._last_resolution
        return [
            "Last action:",
            f"  Actor:   {r.actor_id}",
            f"  Action:  {r.action_key}",
            f"  Intent:  {r.intent if r.intent else '(none)'}",
            f"  Dice:    {r.dice_rolled}",
            f"  Outcome: {r.outcome}",
        ]

    def set_reaction(self, reaction: WorldReaction) -> None:
        self._last_reaction = reaction

    def reaction_section_lines(self) -> list[str]:
        if self._last_reaction is None:
            return ["No reaction yet"]
        r = self._last_reaction
        lines = [f"Deterministic reaction ({r.outcome.upper()}):"]
        if not r.clock_lines and not r.stress_lines:
            lines.append("  (nothing changed)")
            return lines
        for cl in r.clock_lines:
            lines.append(f"  Clock [{cl.label}]: +{cl.ticks} → {cl.new_filled}/{cl.new_status}")
        for sl in r.stress_lines:
            fallout = "  [FALLOUT]" if sl.triggered_fallout else ""
            lines.append(
                f"  Stress [{sl.display_name} / {sl.track_key}]: +{sl.amount} → {sl.new_filled}{fallout}"
            )
        return lines

    def set_current_level_id(self, level_id: str | None) -> None:
        self._current_level_id = level_id

    def set_current_level_room_ids(self, room_ids: set[str]) -> None:
        self._current_level_room_ids = room_ids

    def set_bundle(self, bundle: ContextBundle) -> None:
        self._last_bundle = bundle

    def bundle_section_lines(self) -> list[str]:
        if self._last_bundle is None:
            return ["No bundle built yet"]
        b = self._last_bundle
        omitted = b.provenance.get("omitted", 0)
        lines = [
            f"Context bundle: {b.bundle_id}",
            f"  Cards: {len(b.memory_cards)}  Trimmed: {omitted}",
        ]
        for card in b.memory_cards:
            reason = "importance" if card["memory_id"] in b.must_remember else "retrieved"
            lines.append(f"  - {card['title']} [{reason}]")
        return lines

    def clock_section_lines(self) -> list[str]:
        if self._last_bundle is None:
            return ["No bundle built yet"]
        all_clocks = self._last_bundle.open_clocks
        clocks = [
            c for c in all_clocks
            if not (
                c.get("clock_level") == "level"
                and self._current_level_id is not None
                and c.get("level_id") != self._current_level_id
            )
            and not (
                c.get("clock_level") == "room"
                and self._current_level_room_ids
                and c.get("scope_room_id") not in self._current_level_room_ids
            )
        ]
        if not clocks:
            return ["Clocks: (none)"]
        lines = [f"Clocks: {len(clocks)} active"]
        for c in clocks:
            label = c.get("label", "?")
            filled = c.get("filled", 0)
            segments = c.get("segments", 0)
            clock_level = c.get("clock_level", "dungeon") or "dungeon"
            category = c.get("category")
            scope_room_id = c.get("scope_room_id")
            level_id = c.get("level_id")
            owner_actor_id = c.get("owner_actor_id")
            action_tags = c.get("action_tags") or []

            if clock_level == "room" and scope_room_id:
                level_part = f"room:{scope_room_id}"
            elif clock_level == "level" and level_id:
                level_part = f"level:{level_id}"
            elif clock_level in ("character", "faction") and owner_actor_id:
                display = c.get("owner_display_name") or owner_actor_id
                level_part = f"{clock_level}:{display}"
            else:
                level_part = clock_level

            parts = [level_part]
            if category:
                parts.append(category)
            if action_tags:
                parts.append(f"actions: {','.join(action_tags)}")

            meta = " | ".join(parts)
            lines.append(f"  [{filled}/{segments}] {label} {{{meta}}}")
        return lines

    def resolve_sample_action(
        self,
        request: ActionRequest,
        fixed: list[int] | None = None,
    ) -> ActionResolution:
        resolution, _ = self._rpg.resolve_action(request, fixed=fixed)
        self._last_resolution = resolution
        if self._mem_repo is not None:
            self._mem_repo.save_action_resolution(
                resolution_id=resolution.resolution_id,
                campaign_id=resolution.campaign_id,
                actor_id=resolution.actor_id,
                action_key=resolution.action_key,
                outcome=resolution.outcome,
            )
        return resolution

    def apply_stress(
        self,
        actor_id: str,
        campaign_id: str,
        track: StressTrack,
        amount: int = 1,
    ) -> StressTrack:
        updated, _ = self._rpg.apply_stress(actor_id, campaign_id, track, amount)
        self._last_stress_track = updated
        if self._mem_repo is not None:
            self._mem_repo.save_actor_stress_track(
                actor_id=actor_id,
                track_key=updated.track_key,
                capacity=updated.capacity,
                filled=updated.filled,
            )
        return updated

    def advance_clock(self, clock: ClockState, ticks: int = 1) -> ClockState:
        updated, _ = self._rpg.advance_clock(clock, ticks)
        self._last_clock = updated
        if self._mem_repo is not None:
            self._mem_repo.save_clock(
                clock_id=updated.clock_id,
                campaign_id=updated.campaign_id,
                label=updated.label,
                segments=updated.segments,
                filled=updated.filled,
                status=updated.status,
            )
        return updated

    def generate_sync_report(self) -> list:
        if self._sync_reporter is None:
            return []
        issues = self._sync_reporter.check()
        self._last_sync_issues = issues
        return issues

    def set_proposal_result(self, validation, apply_result=None) -> None:
        self._last_validation = validation
        self._last_apply_result = apply_result

    def proposal_section_lines(self) -> list[str]:
        if self._last_validation is None:
            return ["No proposal yet"]
        v = self._last_validation
        ar = self._last_apply_result
        applied_count = len(ar.applied) if ar is not None else 0
        skipped_count = len(ar.skipped) if ar is not None else 0
        lines = [f"LLM proposal [source: {v.source}]"]
        if v.parse_status is not None:
            lines.append(f"  Parse: {v.parse_status}")
        lines.append(
            f"  Accepted: {len(v.accepted)}  Rejected: {len(v.rejected)}"
            f"  Applied: {applied_count}  Skipped: {skipped_count}"
        )
        for rc in v.rejected:
            lines.append(f"  [REJECTED] {rc.change.kind}: {rc.reason}")
        for ac in v.accepted:
            lines.append(f"  [ACCEPTED] {ac.kind}")
        if ar is not None:
            for sk in ar.skipped:
                lines.append(f"  [SKIPPED] {sk.kind}")
        return lines

    def create_test_memory_note(self, campaign_id: str, title: str) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            type="note",
            title=title,
            summary="Debug test note.",
        )
        self._last_memory_note = entry
        return entry
