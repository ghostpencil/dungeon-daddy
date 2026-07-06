"""Navigation coordination (Phase 51.7, Slice 5).

:class:`NavigationCoordinator` owns the navigation seam extracted from
``PlayView``: engine-validated party moves (``on_exit_move``), the graph
room-select branch (``on_graph_room_select``), party-room focus on load/resume
(``focus_party_room``), and the layout-label helpers (``current_level_rooms`` /
``prepare_vna_exits``) that map rendered-layout geometry onto exit compass
directions.

Pure play-layer object — imports no ``arcade`` (see the package docstring for
the dependency direction). It receives the view's UI/side-effect seams as narrow
callables (ports); it never holds a ``PlayView`` reference.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dungeon_daddy.data.models import Level, Room
    from dungeon_daddy.play.session_context import PlaySessionContext

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _PositionedRoom:
    """A room's rendered-layout geometry + name, for exit compass labels.

    Exposes the same ``x``/``y``/``w``/``h``/``name`` surface a ``Room`` does so
    :func:`dungeon_daddy.rpg.exit_labels.exit_noun_label` can consume it, but the
    coordinates are the layout-pipeline positions the map actually draws.
    """
    x: float
    y: float
    w: float
    h: float
    name: str


class NavigationCoordinator:
    """Applies party moves and reflects the party's location in the UI."""

    def __init__(
        self,
        session: PlaySessionContext,
        *,
        post_message: Callable[[str, str], None],
        request_narration: Callable[[str], None],
        set_selected_room: Callable[[str], None],
        set_current_room: Callable[[str, str, str], None],
        set_scene: Callable[[str, str], None],
        load_level: Callable[..., None],
        update_map_state: Callable[..., None],
        set_viewed_level: Callable[[int], None],
        end_dialogue_on_room_change: Callable[[], None],
        refresh_vna_panel: Callable[[], None],
        save_session: Callable[[], None],
    ) -> None:
        self._session = session
        self._post_message = post_message
        self._request_narration = request_narration
        self._set_selected_room = set_selected_room
        self._set_current_room = set_current_room
        self._set_scene = set_scene
        self._load_level = load_level
        self._update_map_state = update_map_state
        self._set_viewed_level = set_viewed_level
        self._end_dialogue_on_room_change = end_dialogue_on_room_change
        self._refresh_vna_panel = refresh_vna_panel
        self._save_session = save_session

    # -- party-room focus ----------------------------------------------------

    def focus_party_room(self) -> None:
        """Reflect the party's current room in the map + side panels.

        Used on load/resume so the player always opens a save where the party
        actually is: the room is selected on the map (selection frame + detail
        overlay) and the chat/scene panels are populated. No narration.
        """
        session = self._session
        level = session.current_level()
        room = session.current_room()
        if level is None or room is None:
            return
        self._reflect_room(room, level, select=True)

    def _reflect_room(self, room: Room, level: Level, *, select: bool) -> None:
        """Reflect the party's room in the chat + scene panels (and map cursor).

        ``select`` moves the map selection cursor to the room so the selected
        frame and detail/info overlay follow the party — used on load/resume and
        after an exit move (same treatment as a click). A graph room-select
        already carries its own cursor, so it passes ``select=False``.
        """
        if select:
            self._set_selected_room(room.id)
        self._set_current_room(room.name, room.note or "", room.id)
        self._set_scene(room.name, str(level.id))

    def on_exit_move(self, exit_id: str, how: str, *, item_slug: str | None = None) -> None:
        """Apply an engine-validated party move, then narrate the result."""
        from dungeon_daddy.rpg.command import MoveParty
        from dungeon_daddy.rpg.move_party import apply_move_party

        session = self._session
        if session.mem_repo is None or session.campaign_id is None or session.state is None:
            return

        new_session, result = apply_move_party(
            MoveParty(exit_id=exit_id, how=how),
            session.mem_repo, session.campaign_id, session.state,
            extra_inventory_slugs=[item_slug] if item_slug else None,
        )
        if not result.accepted:
            self._post_message("system", f"⚠ Can't move: {result.rejection_reason}")
            return

        old_level_idx = session.state.current_level_idx
        session.state = new_session
        # Walking out of the room closes any open dialogue channel (§4.3).
        self._end_dialogue_on_room_change()
        room = None
        level = None
        if session.dungeon is not None:
            level = session.current_level()
            room = session.current_room()
            total = len(session.dungeon.levels)
            if session.state.current_level_idx != old_level_idx:
                # Advance the viewed level only when the map actually reloads,
                # so paging can't point at a level the map never loaded.
                if level is not None:
                    self._set_viewed_level(session.state.current_level_idx)
                    self._load_level(level, session.state, total)
            else:
                self._update_map_state(session.state, total)
            # ``current_room`` only resolves once ``current_level`` does, so a
            # non-None room implies a non-None level.
            if room is not None and level is not None:
                self._reflect_room(room, level, select=True)

        self._refresh_vna_panel()
        self._save_session()

        if room is not None and level is not None:
            flags = ", ".join(sorted(result.modifier_flags)) or "none"
            self._request_narration(
                f"We move {how} through the exit into {room.name}. (effects: {flags})"
            )

    def on_graph_room_select(self, room_id: str) -> None:
        """Enter the room the player clicked on the graph: select + narrate."""
        session = self._session
        level = session.current_level()
        if level is None or session.state is None or session.dungeon is None:
            return
        room = next((r for r in level.rooms if r.id == room_id), None)
        if room is None:
            return
        session.state.current_room_id = room.id
        if room.id not in session.state.visited_rooms:
            session.state.visited_rooms.append(room.id)
        total = len(session.dungeon.levels)
        self._update_map_state(session.state, total)
        self._reflect_room(room, level, select=False)
        _log.debug("Graph: selected room %s", room.id)
        self._request_narration(f"We enter {room.name}.")
        self._save_session()

    # -- layout-label helpers ------------------------------------------------

    def prepare_vna_exits(
        self, room_context: dict[str, Any], room_id: str
    ) -> dict[str, Any]:
        """Player-facing exit nouns: drop unknown exits and disambiguate labels.

        Hidden/sealed exits aren't surfaced as move targets. Same-type exits
        ('Door' x2) are relabelled with a compass direction, upgrading to the
        destination room name once that room has been visited (immersion-safe —
        see :func:`dungeon_daddy.rpg.exit_labels.exit_noun_label`).
        """
        from dungeon_daddy.rpg.exit_labels import exit_noun_label
        from dungeon_daddy.rpg.room_context import PLAYER_KNOWN_EXIT_STATUSES

        rooms_by_id, from_room = self.current_level_rooms(room_id)
        state = self._session.state
        visited = set(state.visited_rooms) if state else set()
        prepared = [
            {
                **ext,
                "label": exit_noun_label(
                    ext, from_room=from_room,
                    rooms_by_id=rooms_by_id, visited_rooms=visited,
                ),
            }
            for ext in room_context.get("exits", [])
            if ext.get("status") in PLAYER_KNOWN_EXIT_STATUSES
        ]
        return {**room_context, "exits": prepared}

    def current_level_rooms(self, room_id: str) -> tuple[dict[str, Any], Any]:
        """``({room_id: positioned room}, current room)`` for the active level.

        Positions come from the **rendered layout** (the same
        ``run_layout_pipeline`` output the map draws), so exit compass
        directions match what the player sees — the layout re-grids rooms by
        their connections, which can move a raw "far east" room directly south
        of the hub. Falls back to raw geometry if the layout can't be built,
        and to ``({}, None)`` when no dungeon is loaded.
        """
        session = self._session
        if session.dungeon is None or session.state is None:
            return {}, None
        idx = session.state.current_level_idx
        if not (0 <= idx < len(session.dungeon.levels)):
            return {}, None
        from dungeon_daddy.map.dungeon_layout import run_layout_pipeline

        level = session.dungeon.levels[idx]
        names = {r.id: r.name for r in level.rooms}
        try:
            result = run_layout_pipeline(level)
        except Exception:
            raw_rooms = {r.id: r for r in level.rooms}
            return raw_rooms, raw_rooms.get(room_id)
        positioned = {
            rid: _PositionedRoom(
                x=rect.x, y=rect.y, w=rect.w, h=rect.h, name=names.get(rid, ""),
            )
            for rid, rect in result.rooms.items()
        }
        return positioned, positioned.get(room_id)
