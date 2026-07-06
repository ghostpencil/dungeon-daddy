"""World-reaction application (Phase 51.7, Slice 1).

Extracts ``PlayView._apply_world_reaction``: compute the world reaction for a
resolved action, then persist the resulting clock + stress writes **atomically**
in a single DuckDB transaction (the deferred PR #88 fix). On any failure the
partial state is rolled back, the traceback is logged, and a user-facing system
line is posted through the injected ``post_system`` port.

Pure play-layer object — imports no ``arcade`` (see the package docstring for the
dependency direction).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from dungeon_daddy.rpg.models import ClockState, StressTrack

if TYPE_CHECKING:
    from dungeon_daddy.play.session_context import PlaySessionContext
    from dungeon_daddy.rpg.models import ActionResolution, RoomObject, WorldReaction
    from dungeon_daddy.rpg.service import RpgService

_log = logging.getLogger(__name__)

REACTION_FAILURE_LINE = "⚠ Reaction could not be fully applied."

# Capacity used for a stress track the actor has not yet been seeded with — the
# same default ``world_reaction`` assumes (``StressTrack(track_key=...)``), so the
# persisted row and the computed ``new_filled`` agree.
_DEFAULT_STRESS_CAPACITY: int = StressTrack.model_fields["capacity"].default


class ReactionApplier:
    """Computes and atomically persists an action's world reaction."""

    def __init__(
        self,
        session: PlaySessionContext,
        rpg_service: RpgService | None,
        *,
        post_system: Callable[[str], None],
        on_reaction: Callable[[WorldReaction], None] | None = None,
    ) -> None:
        self._session = session
        self._rpg_service = rpg_service
        self._post_system = post_system
        self._on_reaction = on_reaction

    def apply(
        self, resolution: ActionResolution, acted_object: RoomObject | None = None
    ) -> WorldReaction | None:
        session = self._session
        mem_repo = session.mem_repo
        if self._rpg_service is None or mem_repo is None:
            return None
        if session.campaign_id is None:
            return None
        # Reads: fetch persisted world state. A repo read failure is contained
        # (never crashes the caller) but IS surfaced to the GM — the reaction
        # cannot be applied, the same user-visible outcome as a write failure.
        # (Pre-51.7 these reads sat outside the guard and propagated; swallowing
        # them silently was a regression.)
        try:
            threat_clocks = [
                ClockState(**r) for r in mem_repo.get_clocks(session.campaign_id)
            ]
            # Per-actor stress from the repo (the authoritative capacity source —
            # capacity varies per track and can differ from a stale in-memory copy).
            tracks_by_actor = {
                a.actor_id: {
                    t["track_key"]: StressTrack(**t)
                    for t in mem_repo.get_actor_stress_tracks(a.actor_id)
                }
                for a in session.actors
            }
        except Exception:
            _log.exception("world_reaction read failed")
            self._post_system(REACTION_FAILURE_LINE)
            return None

        # Compute: a pure-logic failure degrades silently — nothing was written,
        # so no "could not be fully applied" line, matching the pre-51.7 behavior.
        try:
            pc_pairs = [(a, tracks_by_actor[a.actor_id]) for a in session.actors]
            reaction, _evt = self._rpg_service.react_to_resolution(
                resolution, threat_clocks, pc_pairs,
                current_room_id=(
                    session.state.current_room_id if session.state else None
                ),
                current_level_id=session.current_level_id,
                acted_object=acted_object,
            )
        except Exception:
            _log.exception("world_reaction compute failed")
            return None

        # Writes: atomic. A persistence failure is surfaced to the GM (the
        # deferred PR #88 fix) and leaves no partial state behind.
        try:
            with mem_repo.transaction():
                for cl in reaction.clock_lines:
                    mem_repo.update_clock_progress(
                        clock_id=cl.clock_id,
                        filled=cl.new_filled,
                        status=cl.new_status,
                    )
                for sl in reaction.stress_lines:
                    mem_repo.save_actor_stress_track(
                        actor_id=sl.actor_id,
                        track_key=sl.track_key,
                        capacity=self._track_capacity(
                            tracks_by_actor.get(sl.actor_id), sl.track_key
                        ),
                        filled=sl.new_filled,
                    )
        except Exception:
            _log.exception("world_reaction write failed")
            self._post_system(REACTION_FAILURE_LINE)
            return None

        self._sync_actor_stress(reaction, tracks_by_actor)
        if self._on_reaction is not None:
            self._on_reaction(reaction)
        return reaction

    @staticmethod
    def _track_capacity(tracks: dict[str, StressTrack] | None, track_key: str) -> int:
        """The capacity to persist for ``track_key`` — the track's own if it
        exists, else the shared default (what ``world_reaction`` assumes)."""
        track = tracks.get(track_key) if tracks else None
        return track.capacity if track is not None else _DEFAULT_STRESS_CAPACITY

    def _sync_actor_stress(
        self,
        reaction: WorldReaction,
        tracks_by_actor: dict[str, dict[str, StressTrack]],
    ) -> None:
        """Mirror committed stress into the in-memory roster so panel refreshes
        see the new values without a reload — creating the track if it is new."""
        actors_by_id = {a.actor_id: a for a in self._session.actors}
        for sl in reaction.stress_lines:
            actor = actors_by_id.get(sl.actor_id)
            if actor is None:
                continue
            track = actor.stress.get(sl.track_key)
            if track is None:
                actor.stress[sl.track_key] = StressTrack(
                    track_key=sl.track_key,
                    capacity=self._track_capacity(
                        tracks_by_actor.get(sl.actor_id), sl.track_key
                    ),
                    filled=sl.new_filled,
                )
            else:
                track.filled = sl.new_filled
