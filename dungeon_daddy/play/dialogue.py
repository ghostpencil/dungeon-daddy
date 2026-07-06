"""Dialogue-channel plumbing (Phase 51.7, Slice 3).

:class:`DialogueCoordinator` owns the "Talk to the Dungeon" + NPC dialogue seam
extracted from ``PlayView``: the open-channel :class:`DialogueSession`, begin/end
and room-change close, per-``kind`` line routing, the §4.4 dungeon-voice context
assembly (``agent_inputs`` + its subsystem/objective/knowledge assemblers), and
the ``apply_dungeon_reply`` engine side-effect (the reply bubble + the
engine-authored exchange memory).

The dungeon-voice call runs on a worker thread handed to
:class:`~dungeon_daddy.play.narration.NarrationCoordinator` — its reply is queued
as a ``dungeon``-marked :class:`~dungeon_daddy.play.narration.DMResult` and routed
back to :meth:`apply_dungeon_reply` when the queue is drained on the main thread.

Pure play-layer object — imports no ``arcade`` (see the package docstring for the
dependency direction). It receives the view's UI/side-effect seams as narrow
callables (ports); it never holds a ``PlayView`` reference.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from dungeon_daddy.play.narration import DMResult
from dungeon_daddy.rpg.models import ClockState

if TYPE_CHECKING:
    from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent
    from dungeon_daddy.play.narration import NarrationCoordinator
    from dungeon_daddy.play.session_context import PlaySessionContext
    from dungeon_daddy.rpg.models import ActorState


@dataclass
class DialogueSession:
    """In-memory state for an open dialogue channel (Phase 51 §4.3).

    ``kind`` dispatches the routing: ``"dungeon"`` is the freeform
    Talk-to-the-Dungeon channel, ``"npc"`` is the 50.6 ``sway→willing`` creature
    conversation folded onto the same engine (decision D1). ``turns`` is the
    running exchange (LLM history + memory summary).
    """

    kind: Literal["dungeon", "npc"]
    room_id: str
    target_id: str | None = None
    turns: list[tuple[str, str]] = field(default_factory=list)


class DialogueCoordinator:
    """Owns the open dialogue channel + dungeon-voice context assembly."""

    _INTIMACY_CATEGORY = "dungeon_intimacy"
    _RECENT_MEMORY_LIMIT = 3

    def __init__(
        self,
        session: PlaySessionContext,
        *,
        get_narration: Callable[[], NarrationCoordinator],
        get_voice_agent: Callable[[], DungeonVoiceAgent | None],
        get_acting_actor: Callable[[], ActorState | None],
        post_message: Callable[[str, str], None],
        set_dialogue_mode: Callable[[bool], None],
        set_busy: Callable[[bool], None],
        get_room_context: Callable[[], dict[str, Any]],
    ) -> None:
        self._session = session
        self._get_narration = get_narration
        self._get_voice_agent = get_voice_agent
        self._get_acting_actor = get_acting_actor
        self._post_message = post_message
        self._set_dialogue_mode = set_dialogue_mode
        self._set_busy = set_busy
        self._get_room_context = get_room_context

        # Open dialogue channel, or None when the Action Builder is active.
        self.session: DialogueSession | None = None
        # Seed-authored dungeon persona (populated when a campaign is attached).
        self.dungeon_voice: str | None = None
        self.dungeon_knowledge: list[str] = []

    # -- open / close --------------------------------------------------------

    def begin_dialogue(
        self,
        *,
        kind: Literal["dungeon", "npc"],
        room_id: str,
        target_id: str | None = None,
        opener: str | None = None,
    ) -> None:
        """Open a dialogue channel and swap the chat input to the SAY box.

        Shared by both kinds (decision D1): ``"npc"`` from a ``sway`` on a
        willing creature, ``"dungeon"`` from the resonance-point channel. The
        per-line routing in :meth:`send_line` dispatches by ``kind``.
        """
        self.session = DialogueSession(kind=kind, room_id=room_id, target_id=target_id)
        self._set_dialogue_mode(True)
        if opener:
            self._post_message("system", opener)

    def end_dialogue(self) -> None:
        """Close the open channel and swap the input back to the Action Builder."""
        self.session = None
        self._set_dialogue_mode(False)

    def maybe_end_on_room_change(self) -> None:
        """Close an open channel when the party has left the room it opened in.

        The dungeon channel is bound to its resonance room (spec §4.3); an NPC
        conversation likewise ends when you walk away. A no-op while the party is
        still in the session's room.
        """
        session = self.session
        state = self._session.state
        if session is None or state is None:
            return
        if state.current_room_id != session.room_id:
            self.end_dialogue()

    # -- line routing --------------------------------------------------------

    def send_line(self, text: str) -> None:
        """Route a line typed into the SAY box, dispatched by session ``kind``.

        ``/leave`` closes the channel from either kind. Otherwise the dungeon
        kind runs the freeform voice pipeline; the npc kind is a thin binding
        (D1a) that records the turn and keeps the conversation open.
        """
        session = self.session
        if session is None:
            return
        if text.strip() == "/leave":
            self.end_dialogue()
            return
        if session.kind == "dungeon":
            self.send_dungeon_line(text)
        else:
            self.send_npc_line(text)

    def send_npc_line(self, text: str) -> None:
        """Thin NPC binding (D1a): post the line, record it, stay open.

        Phase 51 fully implements only the dungeon channel; the NPC kind reuses
        the shared session/surface plumbing without a dedicated reply agent.
        """
        session = self.session
        if session is None:
            return
        session.turns.append(("player", text))
        self._post_message("gm", text)

    # -- dungeon channel (Phase 51 "Talk to the Dungeon") --------------------

    def send_dungeon_line(self, text: str) -> None:
        """Send a line to the dungeon voice (off-thread) and queue the reply.

        Echoes/records the player's line immediately, then calls the
        ``DungeonVoiceAgent`` on a worker thread (a network call) handed to the
        narration coordinator. The reply is queued as a dungeon-marked
        ``DMResult``; the queue drain applies the engine side-effects on the
        main thread.
        """
        session = self.session
        if session is None:
            return
        session.turns.append(("player", text))
        self._post_message("gm", text)

        agent = self._get_voice_agent()
        if agent is None:
            self._post_message(
                "system", "The dungeon is silent. (voice agent unavailable)"
            )
            return
        if self._get_narration().is_busy:
            return
        inputs = self.agent_inputs(text)
        self._set_busy(True)

        def _worker() -> DMResult:
            try:
                reply = agent.respond(**inputs)
                return DMResult(content=reply, dungeon=True, player_message=text)
            except Exception as exc:
                return DMResult(content="", error=str(exc), dungeon=True, player_message=text)

        self._get_narration().spawn(_worker)

    def dungeon_intimacy_clock(self) -> ClockState | None:
        """Return the seed-authored non-monotonic intimacy clock, or ``None``.

        Read live from the repo (D3: the clock must pre-exist in the seed; the
        channel is locked when absent). Identified by ``category``.
        """
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return None
        for row in repo.get_clocks(campaign_id):
            if row.get("category") == self._INTIMACY_CATEGORY:
                return ClockState(**row)
        return None

    def begin_dungeon_dialogue(self) -> None:
        """Open the freeform dungeon channel if both gates pass, else lock it.

        Gates (spec §2): the current room is a resonance point AND the intimacy
        clock is at/above threshold. When closed, post the lock reason and leave
        the Action Builder up.
        """
        from dungeon_daddy.rpg.dungeon_channel import dungeon_channel_available

        room_context = self._get_room_context() or {}
        clock = self.dungeon_intimacy_clock()
        available, reason = dungeon_channel_available(room_context, clock)
        if not available:
            self._post_message("system", reason or "")
            return
        state = self._session.state
        room_id = state.current_room_id if state else ""
        self.begin_dialogue(
            kind="dungeon",
            room_id=room_id or "",
            opener="The dungeon stirs, and turns its attention to you.",
        )

    def set_persona(self, voice: str | None, knowledge: list[str]) -> None:
        """Attach the seed-authored dungeon persona (P4 attach-time reader).

        ``window._attach_rpg_context`` resolves the campaign's persona Markdown
        refs and calls this so the voice agent reads them at play time
        (``agent_inputs``). Missing docs → ``(None, [])``.
        """
        self.dungeon_voice = voice
        self.dungeon_knowledge = list(knowledge)

    def recent_memories(self) -> list[Any]:
        """Last few approved memories, for the dungeon-voice context (§4.4)."""
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return []
        from dungeon_daddy.memory.retrieval import MemoryRetriever

        retriever = MemoryRetriever(repo, campaign_id)
        return retriever.query()[: self._RECENT_MEMORY_LIMIT]

    def agent_inputs(self, text: str) -> dict[str, Any]:
        """Assemble the §4.4 ``DungeonVoiceAgent.respond`` kwargs for ``text``.

        Knowledge is the union of completed tiers' ``reveals_knowledge`` (D7); with
        no objectives authored it falls back to the deprecated flat
        ``reveal_knowledge`` band. The agent itself does no gating (D6).
        """
        from dungeon_daddy.rpg.dungeon_channel import (
            active_objective,
            reveal_knowledge,
            unlocked_knowledge,
        )

        clock = self.dungeon_intimacy_clock()
        filled = clock.filled if clock else 0
        segments = clock.segments if clock else 0
        objectives = self.dungeon_objectives()
        if objectives:
            knowledge = unlocked_knowledge(objectives)
        else:
            knowledge = reveal_knowledge(
                self.dungeon_knowledge or [], filled, segments
            )
        active = active_objective(objectives)
        actor = self._get_acting_actor()
        return {
            "dungeon_voice": self.dungeon_voice or "",
            "intimacy_filled": filled,
            "intimacy_segments": segments,
            "dungeon_knowledge": knowledge,
            "player_message": text,
            "actor": actor.slug if actor else "",
            "recent_memories": self.recent_memories(),
            "actor_name": actor.display_name if actor else "",
            "actor_playbook": self._actor_playbook_name(actor),
            "actor_tags": list(actor.tags) if actor else [],
            "systems_status": self.systems_status(),
            "next_objective": active["description"] if active else None,
            "next_objective_location": self.objective_location(active),
            "session_turns": list(self.session.turns) if self.session else [],
        }

    def dungeon_objectives(self) -> list[dict[str, Any]]:
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return []
        return repo.get_objectives(campaign_id)

    def room_labels(self) -> dict[str, str]:
        """Map each ``room_id`` to a human ``"Level N — Room Name"`` label.

        Resolved from the loaded dungeon model so the dungeon voice can cite a
        subsystem's (or objective's) location. Empty when no dungeon is loaded.
        """
        dungeon = self._session.dungeon
        if dungeon is None:
            return {}
        labels: dict[str, str] = {}
        for level in dungeon.levels:
            for room in level.rooms:
                labels[room.id] = f"Level {level.id} — {room.name}"
        return labels

    def systems_status(self) -> list[tuple[str, str, str]]:
        """Truthful subsystem snapshot + location for the dungeon-voice context.

        Each tuple is ``(display_name, current_state, location)`` (§4.2) so the
        dungeon can both report state and say where a subsystem sits.
        """
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return []
        from dungeon_daddy.rpg.dungeon_channel import located_systems_status

        objects = repo.get_objects_for_campaign(campaign_id)
        return located_systems_status(objects, self.room_labels())

    def objective_location(self, active: dict[str, Any] | None) -> str | None:
        """Resolve the active objective's target object to a room label (or None)."""
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if not active or repo is None or campaign_id is None:
            return None
        target_slug = (active.get("completion") or {}).get("target_slug")
        if not target_slug:
            return None
        from dungeon_daddy.rpg.dungeon_channel import object_location

        objects = repo.get_objects_for_campaign(campaign_id)
        return object_location(target_slug, objects, self.room_labels())

    @staticmethod
    def _actor_playbook_name(actor: ActorState | None) -> str | None:
        """Resolve the acting actor's playbook display name for the dungeon (§4.1)."""
        slug = getattr(actor, "playbook_slug", None)
        if not slug:
            return None
        from dungeon_daddy.rpg.playbook import PlaybookLibrary

        try:
            return PlaybookLibrary().get(slug).display_name
        except KeyError:
            return None

    def apply_dungeon_reply(self, player_message: str, reply: str) -> None:
        """Post the dungeon's reply and apply the engine side-effect (§4.7).

        Runs on the main thread (DuckDB single-writer): posts the distinct
        dungeon bubble, then the **engine** drafts a memory of the exchange via
        ``record_dungeon_exchange`` — never the LLM (authority boundary / D6).
        Phase 51.5 (D1/D5): chat no longer ticks intimacy; the objective service
        is the single intimacy-tick source.
        """
        from dungeon_daddy.memory.dungeon_exchange import record_dungeon_exchange

        self._post_message("dungeon", reply)
        session = self.session
        if session is not None:
            session.turns.append(("dungeon", reply))
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return
        actor = self._get_acting_actor()
        record_dungeon_exchange(
            repo,
            campaign_id=campaign_id,
            actor=actor.slug if actor else "",
            player_message=player_message,
            dungeon_reply=reply,
        )
