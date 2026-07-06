"""The live play-session's shared state (Phase 51.7, Slice 0).

:class:`PlaySessionContext` is the single source of truth for a play session's
dungeon, session state, repo/campaign handles, and the actor roster. It replaces
two smells found in the ``play_view`` audit:

1. the party roster read out of the private ``PlayerActionPanel._actors`` widget
   attribute (reached into 9× — panels should be pure displays), and
2. the ``dungeon → level → room`` lookup idiom duplicated ~9× across the view.

Pure domain state — imports no ``arcade`` (see the package docstring for the
dependency direction).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from dungeon_daddy.data.models import Dungeon, Level, Room, SessionState
from dungeon_daddy.rpg.models import ActorState

if TYPE_CHECKING:
    from dungeon_daddy.memory.repository import MemoryRepository


class PlaySessionContext:
    """Mutable holder for the current play session's shared domain state."""

    def __init__(
        self,
        *,
        dungeon: Dungeon | None = None,
        state: SessionState | None = None,
        mem_repo: MemoryRepository | None = None,
        campaign_id: str | None = None,
        actors: Iterable[ActorState] | None = None,
    ) -> None:
        self.dungeon = dungeon
        self.state = state
        self.mem_repo = mem_repo
        self.campaign_id = campaign_id
        self._actors: list[ActorState] = list(actors) if actors is not None else []

    # -- level / room accessors ---------------------------------------------

    def current_level(self) -> Level | None:
        """The :class:`Level` the party is on, or ``None`` if not resolvable."""
        if self.dungeon is None or self.state is None:
            return None
        idx = self.state.current_level_idx
        if idx < 0 or idx >= len(self.dungeon.levels):
            return None
        return self.dungeon.levels[idx]

    def current_room(self) -> Room | None:
        """The :class:`Room` the party is in, or ``None`` if not resolvable."""
        level = self.current_level()
        if level is None or self.state is None or not self.state.current_room_id:
            return None
        return next(
            (r for r in level.rooms if r.id == self.state.current_room_id), None
        )

    @property
    def current_level_id(self) -> str | None:
        """The synthesized ``f"level-{idx+1}"`` id used for clock/level scoping.

        One-based to match the world-reaction level-scope convention (guarded
        end-to-end by ``tests/unit/views/test_play_view_bundle``).
        """
        if self.state is None:
            return None
        return f"level-{self.state.current_level_idx + 1}"

    # -- actor roster --------------------------------------------------------

    @property
    def actors(self) -> list[ActorState]:
        """The loaded player-actor roster (the party)."""
        return self._actors

    def set_actors(self, actors: Iterable[ActorState]) -> None:
        self._actors = list(actors)

    def acting_actor(self, selected_id: str | None = None) -> ActorState | None:
        """The actor a Card acts as: the selected one, else the first PC.

        Falls back to the first roster member when ``selected_id`` is unset or
        no longer names a roster actor; ``None`` only when the roster is empty.
        """
        if not self._actors:
            return None
        if selected_id:
            return next(
                (a for a in self._actors if a.actor_id == selected_id), self._actors[0]
            )
        return self._actors[0]
