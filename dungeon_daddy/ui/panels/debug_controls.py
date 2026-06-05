"""Debug controls — collapsible section in Play Mode for testing RPG/memory systems."""
from __future__ import annotations

import uuid

from dungeon_daddy.memory.models import ContextBundle, MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActionRequest, ActionResolution, ClockState, StressTrack
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
        clocks = self._last_bundle.open_clocks
        if not clocks:
            return ["Clocks: (none)"]
        lines = [f"Clocks: {len(clocks)} active"]
        for c in clocks:
            label = c.get("label", "?")
            filled = c.get("filled", 0)
            segments = c.get("segments", 0)
            lines.append(f"  [{filled}/{segments}] {label}")
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
