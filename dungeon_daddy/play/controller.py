"""PlaySessionController — the play-session composition root (Phase 51.7, Slice 7).

The controller is the seam ``PlayView`` sits behind. It:

1. **owns the five play coordinators** (Action / Navigation / Dialogue / Memory /
   Narration) and wires every coordinator port against the view (its
   :class:`PlayHost`) + the shared :class:`PlaySessionContext`; and
2. **owns the session-facade methods** — session bootstrap
   (``load_dungeon_*`` / ``set_rpg_context`` / ``save_session`` /
   ``load_player_actors`` / ``sync_debug_level_id``) and the domain→panel
   refresh fan-out (``refresh_vna_panel`` / ``refresh_right_panel_from_actors``
   / ``refresh_chat_mini_card`` / ``refresh_memory_state`` /
   ``room_world_flags``) — extracted out of ``PlayView`` so the view keeps only
   drawing, input routing, layout, and overlay-widget management.

The controller does **not** own the context: it receives the one the view's
Slice 0 session bridge owns, so both agree on a single source of truth. No
coordinator holds a ``PlayView`` reference — they hold the narrow port callables
the controller binds here. The controller reaches the view only through the
:class:`PlayHost` protocol (a structural view of the panel widgets + service
handles the ports read); it imports no ``arcade`` (dependency direction
``views → play → (rpg | memory | llm | data)``).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

from dungeon_daddy.data.models import Dungeon, SessionState
from dungeon_daddy.play.actions import ActionOrchestrator
from dungeon_daddy.play.dialogue import DialogueCoordinator
from dungeon_daddy.play.memory_coordinator import MemoryCoordinator
from dungeon_daddy.play.narration import NarrationCoordinator
from dungeon_daddy.play.navigation import NavigationCoordinator
from dungeon_daddy.play.session_context import PlaySessionContext
from dungeon_daddy.rpg.actor_control import filter_player_actors
from dungeon_daddy.rpg.models import ActorState, StressTrack
from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card

if TYPE_CHECKING:
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.memory.models import ContextBundle
    from dungeon_daddy.rpg.service import RpgService

_log = logging.getLogger(__name__)


class PlayHost(Protocol):
    """The narrow view surface the coordinator ports + facade methods read.

    ``PlayView`` satisfies this structurally. The panel widgets are typed
    ``Any`` (they are ``arcade`` UI objects; this module stays ``arcade``-free).
    View-only attributes touched via ``getattr``/``setattr`` in the facade
    methods (``_last_room_context`` / ``_last_actor_dict`` / ``_portraits_dir`` /
    ``_viewed_level_idx`` / ``_action_state`` / ``_dungeon_voice_agent``) are
    intentionally *not* declared here so a bare ``PlayView.__new__`` test host
    that omits them still works.
    """

    _chat: Any
    _map: Any
    _rpg_scene: Any
    _rpg_vna: Any
    _rpg_action: Any
    _rpg_char: Any
    _rpg_memory: Any
    _rpg_fallout: Any
    _rpg_debug: Any
    _repo: DungeonRepository
    _dm_agent: DungeonMasterAgent | None
    _rpg_service: RpgService | None
    _is_test_drive: bool
    _has_memory: bool

    # The view's input-routing delegators the coordinator ports (and a couple of
    # facade sub-calls) fire through — so the delegators stay the single call
    # surface the existing view tests stub/spy, and the call graph is unchanged.
    def _push_things_here_overlay(self) -> None: ...
    def _acting_actor(self) -> ActorState | None: ...
    def _apply_dungeon_reply(self, player_message: str, reply: str) -> None: ...
    def _extract_remember(self, text: str) -> tuple[str | None, str]: ...
    def _auto_remember(self, event: str) -> None: ...
    def _begin_dialogue(
        self,
        *,
        kind: Literal["dungeon", "npc"],
        room_id: str,
        target_id: str | None = None,
        opener: str | None = None,
    ) -> None: ...
    def _on_exit_move(
        self, exit_id: str, how: str, *, item_slug: str | None = None
    ) -> None: ...
    def _clear_dungeon_connection_lock(self, from_room: str, to_room: str) -> None: ...
    def _refresh_vna_panel(self) -> None: ...
    def _refresh_right_panel_from_actors(self, actor_id: str) -> None: ...
    def _maybe_end_dialogue_on_room_change(self) -> None: ...
    def _save_session(self) -> None: ...
    def _refresh_memory_state(self) -> None: ...
    def _load_player_actors(self) -> None: ...


class PlaySessionController:
    """Composition root: builds + owns the five coordinators and the facade."""

    def __init__(self, host: PlayHost, *, session: PlaySessionContext) -> None:
        self._host = host
        self.context = session

        # Coordinator ports route through the host's view delegators (``host._X``),
        # keeping those delegators the single input surface the existing view tests
        # spy/stub. All ports are late-bound (methods or lambdas) so a bare
        # ``PlayView.__new__`` host without the panels still constructs. (Facade
        # *methods* below call sibling controller methods directly; the one
        # exception is ``set_rpg_context`` — see its comment.)

        # -- Narration -------------------------------------------------------
        self.narration = NarrationCoordinator(
            self.context,
            get_dm_agent=lambda: host._dm_agent,
            get_repo=lambda: host._repo,
            get_rpg_service=lambda: host._rpg_service,
            on_busy=lambda busy: host._chat.set_busy(busy),
            post_dm=lambda text: host._chat.add_message("dm", text),
            post_system=lambda text: host._chat.add_message("system", text),
            on_dungeon_reply=lambda pm, reply: host._apply_dungeon_reply(pm, reply),
            extract_remember=lambda text: host._extract_remember(text),
            auto_remember=lambda event: host._auto_remember(event),
            on_bundle_built=lambda bundle: self._set_debug_bundle(bundle),
        )

        # -- Dialogue --------------------------------------------------------
        self.dialogue = DialogueCoordinator(
            self.context,
            get_narration=lambda: self.narration,
            get_voice_agent=lambda: getattr(host, "_dungeon_voice_agent", None),
            get_acting_actor=lambda: host._acting_actor(),
            post_message=self._post,
            set_dialogue_mode=lambda on: host._chat.set_dialogue_mode(on),
            set_busy=lambda on: host._chat.set_busy(on),
            get_room_context=lambda: getattr(host, "_last_room_context", {}) or {},
        )

        # -- Actions ---------------------------------------------------------
        self.actions = ActionOrchestrator(
            self.context,
            get_rpg_service=lambda: host._rpg_service,
            get_dm_agent=lambda: host._dm_agent,
            get_debug=lambda: host._rpg_debug,
            get_narration=lambda: self.narration,
            get_acting_actor=lambda: host._acting_actor(),
            get_nouns=lambda: (
                host._rpg_vna._nouns if hasattr(host, "_rpg_vna") else []
            ),
            get_room_context=lambda: getattr(host, "_last_room_context", {}),
            post_message=self._post,
            begin_dialogue=lambda **kw: host._begin_dialogue(**kw),
            on_exit_move=lambda exit_id, how, item_slug=None: host._on_exit_move(
                exit_id, how, item_slug=item_slug
            ),
            clear_connection_lock=lambda f, t: host._clear_dungeon_connection_lock(f, t),
            refresh_vna_panel=lambda: host._refresh_vna_panel(),
            refresh_right_panel=lambda actor_id: (
                host._refresh_right_panel_from_actors(actor_id)
            ),
            build_request=lambda **kw: host._rpg_action._build_request(**kw),
            format_result=lambda res: host._rpg_action._format_result(res),
            store_result=lambda summary: host._rpg_action.store_result(summary),
        )

        # -- Navigation ------------------------------------------------------
        self.navigation = NavigationCoordinator(
            self.context,
            post_message=self._post,
            request_narration=lambda text: self.narration.request_narration(text),
            set_selected_room=lambda room_id: host._map.set_selected_room(room_id),
            set_current_room=lambda name, note, room_id: host._chat.set_current_room(
                name, note, room_id=room_id
            ),
            set_scene=lambda name, level_id: host._rpg_scene.set_scene(name, level_id),
            load_level=lambda level, state, total: host._map.load(level, state, total),
            update_map_state=lambda state, total: host._map.update_state(state, total),
            set_viewed_level=lambda idx: setattr(host, "_viewed_level_idx", idx),
            end_dialogue_on_room_change=lambda: host._maybe_end_dialogue_on_room_change(),
            refresh_vna_panel=lambda: host._refresh_vna_panel(),
            save_session=lambda: host._save_session(),
        )

        # -- Memory ----------------------------------------------------------
        self.memory = MemoryCoordinator(
            self.context,
            post_message=self._post,
            append_room_event=(
                lambda name, level_id, room_id, room_name, event: (
                    host._repo.append_room_event(
                        name, level_id, room_id, room_name, event
                    )
                )
            ),
            load_room_memory=lambda name, level_id: (
                host._repo.load_room_memory(name, level_id)
            ),
            save_room_memory=lambda name, level_id, content: (
                host._repo.save_room_memory(name, level_id, content)
            ),
            set_entries=lambda entries: host._rpg_memory.set_entries(entries),
            pop_pending_commit=lambda: host._rpg_memory.pop_pending_commit(),
            refresh_memory_state=lambda: host._refresh_memory_state(),
        )

    def _post(self, role: str, text: str) -> None:
        """Shared chat-post seam (defers the ``_chat`` lookup so ``__new__`` hosts work)."""
        self._host._chat.add_message(role, text)

    # ------------------------------------------------------------------
    # Acting-actor selection
    # ------------------------------------------------------------------

    def acting_actor(self) -> ActorState | None:
        """The actor a Card acts as: the selected one, else the first PC."""
        action_state = getattr(self._host, "_action_state", None)
        selected_id = action_state.actor_id if action_state else None
        return self.context.acting_actor(selected_id)

    def clear_connection_lock(self, from_room: str, to_room: str) -> None:
        """Clear lock styling on the dungeon connection so the map re-renders it open."""
        level = self.context.current_level()
        if level is None:
            return
        for conn in level.connections:
            if conn.from_room == from_room and conn.to_room == to_room:
                conn.connection_style = None
                conn.layout_connection_role = None
                break

    # ------------------------------------------------------------------
    # Session bootstrap
    # ------------------------------------------------------------------

    def load_dungeon_transient(self, dungeon: Dungeon) -> None:
        host = self._host
        host._is_test_drive = True
        self.context.dungeon = dungeon
        self.context.state = SessionState(dungeon_id="__test_drive__", current_level_idx=0)
        level = dungeon.levels[0]
        host._map.load(level, self.context.state, len(dungeon.levels))
        host._map.set_loops_visible(True)  # loop chips are a test-drive affordance
        host._map.set_dungeon_title(dungeon.meta.title)
        host._chat.set_mode_label("Play Mode")
        host._chat.add_message(
            "dm",
            f'Loaded "{dungeon.meta.title}" — Level 1: {level.name}. '
            "Click rooms on the map to explore.",
        )
        _log.info("PlayView: loaded dungeon=%s (test drive)", dungeon.meta.title)
        self.refresh_memory_state()
        self.load_player_actors()
        self.sync_debug_level_id()
        self.navigation.focus_party_room()

    def load_dungeon_session(self, dungeon: Dungeon) -> None:
        host = self._host
        host._is_test_drive = False
        self.context.dungeon = dungeon
        save_name = dungeon.meta.effective_name
        existing = host._repo.load_session(save_name)
        if existing is not None:
            self.context.state = existing
            level = dungeon.levels[existing.current_level_idx]
            host._map.load(level, self.context.state, len(dungeon.levels))
            host._map.set_dungeon_title(dungeon.meta.title)
            host._chat.set_mode_label("Play Mode")
            host._chat.add_message(
                "dm",
                f"Resuming session — Level {existing.current_level_idx + 1}: {level.name}.",
            )
        else:
            self.context.state = SessionState(dungeon_id=save_name, current_level_idx=0)
            level = dungeon.levels[0]
            host._map.load(level, self.context.state, len(dungeon.levels))
            host._map.set_dungeon_title(dungeon.meta.title)
            host._chat.set_mode_label("Play Mode")
            host._chat.add_message(
                "dm",
                f'Loaded "{dungeon.meta.title}" — Level 1: {level.name}. '
                "Click rooms on the map to explore.",
            )
        # Loop pattern chips are an authoring/test-drive affordance, not shown in
        # a normal play session.
        host._map.set_loops_visible(False)
        _log.info("PlayView: loaded dungeon=%s (session)", dungeon.meta.title)
        self.refresh_memory_state()
        self.load_player_actors()
        self.sync_debug_level_id()
        self.navigation.focus_party_room()

    def save_session(self) -> None:
        if not self._host._is_test_drive and self.context.state is not None:
            self._host._repo.save_session(self.context.state)

    def set_rpg_context(
        self,
        mem_repo: Any,
        campaign_id: str | None,
        portraits_dir: Path | None = None,
    ) -> None:
        """Update the active RPG repository and campaign id. Closes the previous repo if any."""
        old = self.context.mem_repo
        if old is not None and old is not mem_repo:
            try:
                old.close()
            except Exception:
                pass
        self.context.mem_repo = mem_repo
        self.context.campaign_id = campaign_id
        setattr(self._host, "_portraits_dir", portraits_dir)
        # Both sub-calls route through the host delegators (not ``self.*``): a view
        # test stubs ``view._load_player_actors`` to isolate the on-load VNA refresh,
        # so this attach point must honour that seam.
        self._host._load_player_actors()
        # set_rpg_context runs *after* load_dungeon_session (where focus_party_room
        # fires while mem_repo is still None), so this is the first point where the
        # room, actors, and repo are all available. Populate the in-chat Action
        # Builder now so it is usable on load.
        self._host._refresh_vna_panel()

    def sync_debug_level_id(self) -> None:
        host = self._host
        state = self.context.state
        if host._rpg_debug is None or state is None:
            return
        idx = state.current_level_idx
        level_id = self.context.current_level_id
        if level_id is not None:
            host._rpg_debug.set_current_level_id(level_id)
        if self.context.dungeon is not None:
            room_ids = {r.id for r in self.context.dungeon.levels[idx].rooms}
            host._rpg_debug.set_current_level_room_ids(room_ids)

    # ------------------------------------------------------------------
    # Player actors + panel refresh fan-out
    # ------------------------------------------------------------------

    def load_player_actors(self) -> None:
        mem_repo = self.context.mem_repo
        if mem_repo is None:
            return
        state = self.context.state
        if state is None:
            return
        campaign_id = self.context.campaign_id or state.dungeon_id
        raw = mem_repo.get_actors_by_campaign(campaign_id)
        actor_states = []
        for a in raw:
            ratings = {
                r["action_key"]: r["rating"]
                for r in mem_repo.get_actor_action_ratings(a["actor_id"])
            }
            stress = {
                t["track_key"]: StressTrack(
                    track_key=t["track_key"],
                    capacity=t["capacity"],
                    filled=t["filled"],
                )
                for t in mem_repo.get_actor_stress_tracks(a["actor_id"])
            }
            actor_states.append(ActorState(
                actor_id=a["actor_id"],
                campaign_id=a["campaign_id"],
                actor_type=a["actor_type"],
                slug=a["slug"],
                display_name=a["display_name"],
                status=a["status"],
                actions=ratings,
                stress=stress,
                playbook_slug=a.get("playbook_slug"),
            ))
        pc_actors = filter_player_actors(actor_states)
        self.context.set_actors(pc_actors)
        self._host._rpg_char.set_party(pc_actors)
        if pc_actors:
            self.refresh_right_panel_from_actors(pc_actors[0].actor_id)
        pc_ids = [a.actor_id for a in pc_actors]
        action_state = getattr(self._host, "_action_state", None)
        if pc_ids and action_state is not None:
            action_state.set_actor_roster(pc_ids)
        self.refresh_chat_mini_card()

    def refresh_right_panel_from_actors(self, actor_id: str) -> None:
        """Sync right panel inspector with the actor who just acted."""
        actors = self.context.actors
        if not actors:
            return
        actor = next((a for a in actors if a.actor_id == actor_id), actors[0])
        self._host._rpg_char.set_actor(actor)
        if actor.playbook_slug:
            from dungeon_daddy.rpg.playbook import PlaybookLibrary
            try:
                self._host._rpg_char.set_playbook(PlaybookLibrary().get(actor.playbook_slug))
            except KeyError:
                self._host._rpg_char.set_playbook(None)
        else:
            self._host._rpg_char.set_playbook(None)
        mem_repo = self.context.mem_repo
        if mem_repo is not None:
            self._host._rpg_char.set_abilities(mem_repo.get_actor_abilities(actor.actor_id))
        self.refresh_chat_mini_card()
        if mem_repo is not None and self.context.campaign_id:
            from dungeon_daddy.rpg.models import FalloutRecord
            raw = mem_repo.get_fallout_records(self.context.campaign_id, actor.actor_id)
            entries = [
                FalloutRecord(
                    fallout_id=r["fallout_id"],
                    campaign_id=r["campaign_id"],
                    actor_id=r["actor_id"],
                    track_key=r["track_key"],
                    severity=r["severity"],
                    title=r["title"],
                    summary=r["summary"],
                    status=r["status"],
                )
                for r in raw
            ]
            self._host._rpg_fallout.set_entries(entries)

    def refresh_chat_mini_card(self) -> None:
        action_state = getattr(self._host, "_action_state", None)
        if action_state is None:
            return
        actor_id = action_state.actor_id
        actors = self.context.actors
        actor = next((a for a in actors if a.actor_id == actor_id), None) if actor_id else None
        portraits_dir = getattr(self._host, "_portraits_dir", None)
        self._host._chat.set_actor_mini_card(
            build_actor_mini_card(actor, portraits_dir=portraits_dir) if actor else None
        )
        self._host._chat.set_has_multiple_actors(action_state.has_multiple_actors)

    def room_world_flags(self, room_id: str) -> set[str]:
        """World-context flags gating conditional adverbs (mirrors the room-context build)."""
        flags: set[str] = set()
        actors = self.context.actors
        if max((a.actions.get("sense", 0) for a in actors), default=0) >= 1:
            flags.add("can_sense")
        mem_repo = self.context.mem_repo
        cid = self.context.campaign_id
        if mem_repo is None or cid is None:
            return flags
        exits = mem_repo.get_exits_by_room(cid, room_id)
        if any(e.get("status") == "one_way" for e in exits):
            flags.add("one_way")
        if any(e.get("connector_type") == "ritual_gate" for e in exits):
            flags.add("ritual_connector")
        if any(
            o["archetype"] == "trap" and o["current_state"] == "armed"
            for o in mem_repo.get_objects_by_room(cid, room_id)
        ):
            flags.add("armed_trap")
        return flags

    def refresh_vna_panel(self) -> None:
        """Populate the VNA action panel from the current room + acting actor."""
        from dungeon_daddy.memory.context_bundle import build_room_noun_context

        host = self._host
        mem_repo = self.context.mem_repo
        cid = self.context.campaign_id
        state = self.context.state
        if mem_repo is None or cid is None or state is None or not state.current_room_id:
            return
        actor = self.acting_actor()
        if actor is None:
            return
        room_id = state.current_room_id
        room_context = build_room_noun_context(mem_repo, cid, room_id)
        room_context = self.navigation.prepare_vna_exits(room_context, room_id)
        # Party PCs move as a group — their location is in session state, not
        # per-actor room_id, so we inject them here from the loaded actor roster.
        all_actors = self.context.actors
        room_context = {
            **room_context,
            "party": [
                {"actor_id": a.actor_id, "display_name": a.display_name}
                for a in all_actors
                if a.actor_id != actor.actor_id
            ],
        }
        actor_dict = {
            "actor_id": actor.actor_id,
            "display_name": actor.display_name,
            "carried_items": mem_repo.get_items_by_actor(actor.actor_id),
        }
        host._rpg_vna.set_context(
            actor_abilities=mem_repo.get_actor_abilities(actor.actor_id),
            room_context=room_context,
            actor=actor_dict,
            playbook_slug=actor.playbook_slug or "",
            world_flags=self.room_world_flags(room_id),
        )
        # Retain the prepared context so the lighter overlay-push path
        # (_on_overlay_noun_click) can rebuild the "Things Here" view-model
        # without re-running set_context, which would reset the noun selection.
        setattr(host, "_last_room_context", room_context)
        setattr(host, "_last_actor_dict", actor_dict)
        # Feed the map's "Things Here" overlay from the same room context, so it
        # auto-tracks the current room (Phase 50.6 §5). The in-chat Action
        # Builder reads _rpg_vna's options live each draw, so no widget rebuild
        # is needed here.
        host._push_things_here_overlay()

    # ------------------------------------------------------------------
    # Debug / memory panel state
    # ------------------------------------------------------------------

    def _set_debug_bundle(self, bundle: ContextBundle) -> None:
        if self._host._rpg_debug is not None:
            self._host._rpg_debug.set_bundle(bundle)

    def refresh_memory_state(self) -> None:
        self._host._has_memory = self.memory.has_level_memory()
