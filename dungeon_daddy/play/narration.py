"""DM narration plumbing (Phase 51.7, Slice 2).

:class:`NarrationCoordinator` owns the LLM-narration seam extracted from
``PlayView``: the DM message history + compaction, the context-bundle snapshot,
the worker-thread spawn, and the thread-safe result queue + busy flag. It
collapses the 4-line narration-entry idiom (``_compact_history`` → append user
turn → ``set_busy`` → ``_spawn_dm_thread``) — duplicated 8× across the view —
into a single :meth:`request_narration`, and drains its own queue via
:meth:`poll` (called from ``PlayView.on_update``).

Threading rules (``spec/ARCHITECTURE.md``) unchanged: one active LLM call per
view, results delivered through a thread-safe queue drained on the main thread,
DuckDB reads/writes on the main thread only (the bundle + room-memory snapshots
are taken before the worker starts).

Pure play-layer object — imports no ``arcade`` (see the package docstring for the
dependency direction). It receives the view's UI/side-effect seams as narrow
callables (ports); it never holds a ``PlayView`` reference.
"""
from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dungeon_daddy.llm.lookup_tool import (
    LookupRecord,
    build_lookup_executor,
    bundle_entity_ids,
)
from dungeon_daddy.llm.provider import LLMMessage, LLMToolCall
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.lookup import LookupService
from dungeon_daddy.rpg.actor_control import filter_player_actors
from dungeon_daddy.rpg.models import ActorState

if TYPE_CHECKING:
    from collections.abc import Callable as _Callable

    from dungeon_daddy.data.models import Level, Room
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.memory.models import ContextBundle
    from dungeon_daddy.play.session_context import PlaySessionContext
    from dungeon_daddy.rpg.service import RpgService

_log = logging.getLogger(__name__)

_TOKEN_BUDGET = 2000


@dataclass
class DMResult:
    content: str
    error: str | None = None
    # Phase 51: a dungeon-channel reply (routed to on_dungeon_reply on drain,
    # not the DM narration path). player_message carries the line for the memory
    # summary written engine-side after the reply.
    dungeon: bool = False
    player_message: str | None = None
    # Slice B4e: narrator `lookup_world` calls made on the worker thread, carried
    # back so `poll()` can surface them in the debug panel (L6 provenance).
    lookups: list[LookupRecord] = field(default_factory=list)


class NarrationCoordinator:
    """Owns the DM-narration history, context bundle, worker thread, and queue."""

    def __init__(
        self,
        session: PlaySessionContext,
        *,
        get_dm_agent: Callable[[], DungeonMasterAgent | None],
        get_repo: Callable[[], DungeonRepository],
        get_rpg_service: Callable[[], RpgService | None],
        on_busy: Callable[[bool], None],
        post_dm: Callable[[str], None],
        post_system: Callable[[str], None],
        on_dungeon_reply: Callable[[str, str], None],
        extract_remember: Callable[[str], tuple[str | None, str]],
        auto_remember: Callable[[str], None],
        on_bundle_built: Callable[[ContextBundle], None] | None = None,
        on_lookups: Callable[[list[LookupRecord]], None] | None = None,
    ) -> None:
        self._session = session
        self._get_dm_agent = get_dm_agent
        self._get_repo = get_repo
        self._get_rpg_service = get_rpg_service
        self._on_busy = on_busy
        self._post_dm = post_dm
        self._post_system = post_system
        self._on_dungeon_reply = on_dungeon_reply
        self._extract_remember = extract_remember
        self._auto_remember = auto_remember
        self._on_bundle_built = on_bundle_built
        self._on_lookups = on_lookups

        self._queue: queue.Queue[DMResult] = queue.Queue()
        self._llm_busy = False
        self._active_thread: threading.Thread | None = None
        self._history: list[LLMMessage] = []

    # -- shared state (bridged to the view for the __new__ test pattern) ------

    @property
    def history(self) -> list[LLMMessage]:
        return self._history

    @history.setter
    def history(self, value: list[LLMMessage]) -> None:
        # Alias the assigned list (not a copy) to preserve the historical
        # ``self._dm_history = <list>`` attribute-assignment semantics.
        self._history = value

    def clear_history(self) -> None:
        self._history = []

    @property
    def is_busy(self) -> bool:
        return self._llm_busy

    @is_busy.setter
    def is_busy(self, value: bool) -> None:
        self._llm_busy = value

    @property
    def queue(self) -> queue.Queue[DMResult]:
        return self._queue

    @queue.setter
    def queue(self, value: queue.Queue[DMResult]) -> None:
        self._queue = value

    @property
    def active_thread(self) -> threading.Thread | None:
        return self._active_thread

    @active_thread.setter
    def active_thread(self, value: threading.Thread | None) -> None:
        self._active_thread = value

    # -- public seam ----------------------------------------------------------

    def request_narration(self, user_content: str) -> None:
        """Append a user turn and spawn the DM narrator for the party's room.

        Collapses the historical 4-line idiom. Callers guard the "no room
        selected" case (each posts its own system line); this resolves the
        current room/level from the session and is a no-op if unresolvable.
        """
        room = self._session.current_room()
        level = self._session.current_level()
        if room is None or level is None:
            return
        self.compact_history()
        self._history.append(LLMMessage(role="user", content=user_content))
        self._on_busy(True)
        self.spawn_dm_thread(room, level)

    def poll(self) -> None:
        """Drain one queued result on the main thread and route it.

        Clears the busy flag, then dispatches: an error posts a system line, a
        dungeon reply routes to ``on_dungeon_reply``, and a DM narration is
        run through remember-extraction, appended to history, and displayed.
        """
        try:
            result = self._queue.get_nowait()
        except queue.Empty:
            return
        self._llm_busy = False
        self._on_busy(False)
        if self._on_lookups is not None:
            # Forwarded even when empty: a lookup-free turn must clear the
            # panel, else an earlier turn's record reads as this one's.
            self._on_lookups(result.lookups)
        if result.error:
            self._post_system(f"⚠ The dungeon is silent. ({result.error})")
            return
        if result.dungeon:
            self._on_dungeon_reply(result.player_message or "", result.content)
            return
        remembered, display = self._extract_remember(result.content)
        self._history.append(LLMMessage(role="assistant", content=display))
        self._post_dm(display)
        if remembered:
            self._auto_remember(remembered)

    def spawn(self, worker: Callable[[], DMResult]) -> None:
        """Run ``worker`` on a daemon thread under the busy guard, enqueuing its
        :class:`DMResult`. The worker builds the result (incl. its own error
        result) — used by the dungeon-voice channel. No-op if already busy.
        """
        if self._llm_busy:
            return
        self._llm_busy = True

        def _run() -> None:
            try:
                self._queue.put(worker())
            finally:
                self._llm_busy = False

        t = threading.Thread(target=_run, daemon=True)
        self._active_thread = t
        t.start()

    # -- narration plumbing ---------------------------------------------------

    def compact_history(self) -> None:
        """Drop the oldest exchange pairs while the history exceeds the budget."""
        while len(self._history) >= 2:
            tokens = sum(len(m.content) for m in self._history) // 4
            if tokens <= _TOKEN_BUDGET:
                break
            self._history.pop(0)
            self._history.pop(0)

    def build_context_bundle(self) -> ContextBundle | None:
        """Build a ContextBundle snapshot on the main thread.

        Returns ``None`` when RPG state is unavailable. Notifies
        ``on_bundle_built`` (the DBG panel) when a bundle is produced.
        """
        session = self._session
        rpg_service = self._get_rpg_service()
        if rpg_service is None or session.mem_repo is None or session.state is None:
            return None
        campaign_id = session.campaign_id or session.state.dungeon_id
        raw_actors = session.mem_repo.get_actors_by_campaign(campaign_id)
        actor_states = [
            ActorState(
                actor_id=a["actor_id"],
                campaign_id=a["campaign_id"],
                actor_type=a["actor_type"],
                slug=a["slug"],
                display_name=a["display_name"],
                status=a["status"],
            )
            for a in raw_actors
        ]
        focus_ids = [a.actor_id for a in filter_player_actors(actor_states)]
        builder = ContextBundleBuilder(
            campaign_id=campaign_id,
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=focus_ids,
            token_budget=_TOKEN_BUDGET,
            current_room_id=session.state.current_room_id,
        )
        try:
            bundle = builder.build(session.mem_repo)
            if self._on_bundle_built is not None:
                self._on_bundle_built(bundle)
            return bundle
        except Exception:
            _log.exception("ContextBundle build failed — proceeding without bundle")
            return None

    def _build_lookup_executor(
        self, bundle: ContextBundle | None, records: list[LookupRecord]
    ) -> _Callable[[LLMToolCall], str] | None:
        """The read-only `lookup_world` executor for the DM tool loop (§10).

        Scopes a :class:`LookupService` to the same campaign as the bundle and
        seeds the L7 overlap set from the bundle's entity ids. ``None`` when
        there is no repo *or* no session state (the agent falls back to the
        plain ``complete`` path).
        The executor runs on the worker thread; its reads go through the repo's
        L5 read lock. Each call's :class:`LookupRecord` is appended to
        ``records`` (worker-thread-local) so the worker can carry them back to
        the main thread on the :class:`DMResult` for the debug panel (B4e/L6).
        """
        mem_repo = self._session.mem_repo
        state = self._session.state
        if mem_repo is None or state is None:
            return None
        campaign_id = self._session.campaign_id or state.dungeon_id
        service = LookupService(mem_repo, campaign_id)
        ids = bundle_entity_ids(bundle) if bundle is not None else set()
        return build_lookup_executor(service, ids, on_lookup=records.append)

    def spawn_dm_thread(self, room: Room, level: Level) -> None:
        """Snapshot the room memory + context bundle and run the DM agent off
        the main thread, queuing its reply. No-op if a call is already in
        flight; queues an error result when no DM agent is configured.
        """
        if self._llm_busy:
            return
        agent = self._get_dm_agent()
        if agent is None:
            self._queue.put(
                DMResult(content="", error="DM agent unavailable — OPENAI_API_KEY not set.")
            )
            return
        session = self._session
        assert session.state is not None
        assert session.dungeon is not None
        repo = self._get_repo()
        memory = repo.load_room_memory(session.state.dungeon_id, level.id)
        bundle = self.build_context_bundle()
        lookups: list[LookupRecord] = []
        lookup = self._build_lookup_executor(bundle, lookups)
        self._llm_busy = True
        _history = list(self._history)
        _dungeon = session.dungeon

        def _run() -> None:
            try:
                response = agent.respond(
                    history=_history,
                    room=room,
                    level=level,
                    dungeon=_dungeon,
                    room_memory=memory,
                    context_bundle=bundle,
                    lookup=lookup,
                )
                self._queue.put(DMResult(content=response, lookups=lookups))
            except Exception as exc:
                self._queue.put(DMResult(content="", error=str(exc), lookups=lookups))
            finally:
                self._llm_busy = False

        t = threading.Thread(target=_run, daemon=True)
        self._active_thread = t
        t.start()
