"""Action orchestration (Phase 51.7, Slice 4).

:class:`ActionOrchestrator` owns the action seam extracted from ``PlayView``:
the ``on_vna_submit`` dispatch tree (dialogue gate, look/activate/use branches),
the card roll path, validated command application + objective advancement, the
obstacle seams (contested approaches + DM-ruled resolutions), the proposal
pipeline, and the world-reaction application (via Slice 1's
:class:`~dungeon_daddy.play.reaction_applier.ReactionApplier`).

Pure play-layer object — imports no ``arcade`` (see the package docstring for
the dependency direction). It receives the view's UI/side-effect seams as
narrow callables (ports); it never holds a ``PlayView`` reference.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
    from dungeon_daddy.play.narration import NarrationCoordinator
    from dungeon_daddy.play.session_context import PlaySessionContext
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.command import PlayerCommand
    from dungeon_daddy.rpg.dice import Outcome
    from dungeon_daddy.rpg.models import (
        ActionResolution,
        ActorState,
        RoomObject,
        WorldReaction,
    )
    from dungeon_daddy.rpg.obstacles import ObstacleRollResolution
    from dungeon_daddy.rpg.proposal_validator import ValidationResult
    from dungeon_daddy.rpg.service import RpgService
    from dungeon_daddy.ui.panels.debug_controls import DebugControls

_log = logging.getLogger(__name__)


def describe_spawned_loot(transition: dict[str, Any], room_items: list[dict[str, Any]]) -> str:
    """Deterministic note naming the item a transition reveals, for the narrator.

    When a container transition carries ``spawns_item_slug`` and that item is now
    present in the room, return ``"Name — description"`` so the DM narrator's
    prose reflects reality (it actually finds the loot). Returns ``""`` when the
    transition spawns nothing or the item isn't in the room.
    """
    slug = transition.get("spawns_item_slug")
    if not slug:
        return ""
    item = next((i for i in room_items if i.get("slug") == slug), None)
    if item is None:
        return ""
    name = item.get("display_name") or slug
    desc = (item.get("description") or "").strip()
    return f"{name} — {desc}" if desc else name


class ActionOrchestrator:
    """Routes validated cards/rolls/commands through the RPG engine."""

    def __init__(
        self,
        session: PlaySessionContext,
        *,
        get_rpg_service: Callable[[], RpgService | None],
        get_dm_agent: Callable[[], DungeonMasterAgent | None],
        get_debug: Callable[[], DebugControls | None],
        get_narration: Callable[[], NarrationCoordinator],
        get_acting_actor: Callable[[], ActorState | None],
        get_nouns: Callable[[], list[Any]],
        get_room_context: Callable[[], dict[str, Any]],
        post_message: Callable[[str, str], None],
        begin_dialogue: Callable[..., None],
        on_exit_move: Callable[..., None],
        clear_connection_lock: Callable[[str, str], None],
        refresh_vna_panel: Callable[[], None],
        refresh_right_panel: Callable[[str], None],
        build_request: Callable[..., Any],
        format_result: Callable[[ActionResolution], dict[str, Any]],
        store_result: Callable[[dict[str, Any]], None],
    ) -> None:
        self._session = session
        self._get_rpg_service = get_rpg_service
        self._get_dm_agent = get_dm_agent
        self._get_debug = get_debug
        self._get_narration = get_narration
        self._get_acting_actor = get_acting_actor
        self._get_nouns = get_nouns
        self._get_room_context = get_room_context
        self._post_message = post_message
        self._begin_dialogue = begin_dialogue
        self._on_exit_move = on_exit_move
        self._clear_connection_lock = clear_connection_lock
        self._refresh_vna_panel = refresh_vna_panel
        self._refresh_right_panel = refresh_right_panel
        self._build_request = build_request
        self._format_result = format_result
        self._store_result = store_result

    # -- card dispatch -----------------------------------------------------------

    def on_vna_submit(self, card: ActionCard) -> None:
        """Route a validated ``ActionCard`` to the engine.

        Three branches: (1) ``look`` — read-only description fetch, no dice,
        no state change; (2) mutation verbs via ``resolve_card`` (``activate``
        pre-routes through trigger selection); (3) skill verbs — action roll.
        """
        from dungeon_daddy.rpg.action_options import (
            DIALOGUE_VERBS,
            SOURCE_EXIT,
            SOURCE_LOCKED_EXIT,
            SOURCE_OBJECT,
            VERB_ACTIVATE,
            VERB_LOOK,
            VERB_USE,
            is_speakable,
        )
        from dungeon_daddy.rpg.action_resolution import resolve_card
        from dungeon_daddy.rpg.command import MoveParty

        session = self._session
        actor = self._get_acting_actor()
        if actor is None:
            return

        # Dialogue gate (Phase 50.6 Slice 10, §6): a sway/talk verb aimed at a
        # *speakable* creature opens the contextual SAY box instead of rolling.
        # A hostile/wary target falls through to the normal contested roll.
        if card.verb in DIALOGUE_VERBS:
            noun = next(
                (n for n in self._get_nouns() if n.noun_id == card.noun_id), None
            )
            room_context = self._get_room_context()
            if noun is not None and is_speakable(noun, room_context):
                room_id = session.state.current_room_id if session.state else ""
                self._begin_dialogue(
                    kind="npc",
                    room_id=room_id or "",
                    target_id=noun.noun_id,
                    opener=f"You open a conversation with {noun.label}.",
                )
                return

        if card.verb == VERB_LOOK:
            self.on_look_submit(card)
            return

        if card.verb == VERB_ACTIVATE:
            self.on_activate_submit(card, actor)
            return

        if card.verb == VERB_USE and card.target_id is not None:
            target_noun = next(
                (n for n in self._get_nouns() if n.noun_id == card.target_id),
                None,
            )
            if target_noun and target_noun.source in {SOURCE_EXIT, SOURCE_LOCKED_EXIT}:
                item_noun = next(
                    (n for n in self._get_nouns() if n.noun_id == card.noun_id),
                    None,
                )
                item_slug = item_noun.slug if item_noun else None
                repo = session.mem_repo
                if item_slug and repo is not None:
                    from dungeon_daddy.rpg.unlock_exit import clear_exit_key_requirement
                    exit_row = repo.get_exit_by_id(card.target_id)
                    if exit_row and exit_row.get("requires_item_slug") == item_slug:
                        clear_exit_key_requirement(
                            card.target_id, session.campaign_id or "", repo
                        )
                        self._clear_connection_lock(
                            exit_row["from_room_id"], exit_row["to_room_id"]
                        )
                        from dungeon_daddy.rpg.exit_labels import LOCK_PREFIX
                        exit_label = target_noun.label.removeprefix(LOCK_PREFIX)
                        self._post_message("system", f"{exit_label}: unlocked.")
                        self._refresh_vna_panel()
                        return
                self._on_exit_move(card.target_id, card.adverb, item_slug=item_slug)
                return
            if target_noun and target_noun.source == SOURCE_OBJECT:
                from dungeon_daddy.rpg.action_options import ActionCard
                activate_card = ActionCard(
                    verb=VERB_ACTIVATE, noun_id=card.target_id, adverb=card.adverb,
                )
                self.on_activate_submit(activate_card, actor)
                return

        command = resolve_card(card, actor_id=actor.actor_id)
        if command is None:
            self.resolve_vna_roll(card, actor)
        elif isinstance(command, MoveParty):
            self._on_exit_move(command.exit_id, command.how)
        else:
            self.apply_vna_command(command)

    # -- look branch (read-only) -----------------------------------------------

    def on_look_submit(self, card: ActionCard) -> None:
        """Read-only branch: fetch the noun's authoritative description and post it.

        No dice rolled, no state changed. The description is ground truth —
        it can gate puzzles (e.g. journal → key clue) and must never be
        LLM-invented. The chat bubble makes it visible; the DM agent sees it
        in history for narration context on subsequent turns.
        """
        description = self.look_up_noun_description(card.noun_id)
        noun_label = self._noun_label_for(card.noun_id) or card.noun_id
        if description:
            self._post_message("system", f"{noun_label}: {description}")
        else:
            self._post_message("system", f"⚠ Nothing to read about {noun_label}.")

    def look_up_noun_description(self, noun_id: str) -> str | None:
        """Return the authoritative description for ``noun_id``, or ``None``."""
        repo = self._session.mem_repo
        if repo is None:
            return None
        obj = repo.get_room_object(noun_id)
        if obj is not None:
            return obj.get("description") or None
        campaign_id = self._session.campaign_id
        if campaign_id is not None:
            items = repo.get_items(campaign_id)
            item = next((i for i in items if i["item_id"] == noun_id), None)
            if item is not None:
                return item.get("description") or None
        actor = repo.get_actor(noun_id)
        if actor is not None:
            return actor.get("description") or actor.get("display_name") or None
        return None

    # -- activate branch ---------------------------------------------------------

    def on_activate_submit(self, card: ActionCard, actor: ActorState) -> None:
        """Handle ``activate`` verb: pick trigger from the object, then route.

        Looks up the object's current transitions, selects the first one
        matching the current state, and routes deterministic transitions to the
        command pipeline and contested transitions to the action-roll path.
        """
        from dungeon_daddy.rpg.action_options import ActionCard
        from dungeon_daddy.rpg.action_resolution import resolve_card

        repo = self._session.mem_repo
        if repo is None or self._session.campaign_id is None:
            return

        obj = repo.get_room_object(card.noun_id)
        if obj is None:
            self._post_message("system", f"⚠ Object not found: {card.noun_id}")
            return

        transition = next(
            (t for t in obj.get("transitions", [])
             if t.get("from_state") == obj.get("current_state")),
            None,
        )
        if transition is None:
            self._post_message("system", "⚠ Nothing to do with this object right now.")
            return

        if transition.get("contested"):
            roll_verb = transition.get("action_verb") or "fight"
            roll_card = ActionCard(verb=roll_verb, noun_id=card.noun_id, adverb=card.adverb)
            self.resolve_vna_roll(roll_card, actor)
        else:
            command = resolve_card(card, actor_id=actor.actor_id, trigger=transition["trigger"])
            if self.apply_vna_command(command):
                noun_label = obj.get("display_name") or card.noun_id
                from_state = obj.get("current_state", "")
                to_state = transition.get("to_state", "activated")
                self._post_message("system", f"{noun_label}: {to_state}.")
                self.narrate_object_transition(
                    actor, noun_label, from_state, to_state, transition
                )

    def narrate_object_transition(
        self,
        actor: ActorState,
        noun_label: str,
        from_state: str,
        to_state: str,
        transition: dict[str, Any],
    ) -> None:
        """Inject the deterministic transition result into DM history and request narration."""
        if self._session.dungeon is None or self._session.state is None:
            return
        room = self._session.current_room()
        if room is None:
            return
        content = (
            f"{actor.display_name} {transition.get('trigger', 'activates')} the {noun_label}. "
            f"[{noun_label}: {from_state} → {to_state}]"
        )
        # If the transition just revealed loot, name it so the narrator's prose
        # matches reality (e.g. opening the locker actually finds the journal).
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is not None and campaign_id is not None:
            room_items = repo.get_items_by_room(campaign_id, room.id)
            loot = describe_spawned_loot(transition, room_items)
            if loot:
                content += f" [revealed inside: {loot}]"
        self._get_narration().request_narration(content)

    # -- command application ---------------------------------------------------

    def apply_vna_command(self, command: PlayerCommand | None) -> bool:
        """Validate + apply a non-move mutation command, then refresh.

        Returns True if the command was accepted and applied, False if rejected.
        """
        from dungeon_daddy.rpg.command_applier import apply_command
        from dungeon_daddy.rpg.command_validator import validate_command

        if command is None:
            return False
        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return False
        state = self._session.state
        room_id = state.current_room_id if state else None
        validation = validate_command(
            command, repo, campaign_id, party_room_id=room_id,
        )
        if not validation.accepted:
            self._post_message(
                "system", f"⚠ Can't do that: {validation.rejection_reason}"
            )
            return False
        apply_command(command, validation, repo, campaign_id)
        self.advance_objectives()
        self._refresh_vna_panel()
        return True

    # -- chat-side roll paths (no noun — intent/action-key based) ----------------

    def run_chat_action(
        self,
        campaign_id: str,
        actor_id: str,
        action_key: str,
        intent: str,
    ) -> None:
        from dungeon_daddy.ui.mechanical_bubble import format_mechanical_bubble

        session = self._session
        rpg_service = self._get_rpg_service()
        if rpg_service is None:
            self._post_message("system", "RPG service unavailable.")
            return
        actor = next(
            (a for a in session.actors if a.actor_id == actor_id),
            None,
        )
        dice_pool = (actor.actions.get(action_key) or 1) if actor else 1
        actor_name = actor.display_name if actor else actor_id
        request = self._build_request(
            campaign_id=campaign_id,
            actor_id=actor_id,
            intent=intent,
            action_key=action_key,
            push_yourself=False,
            momentum_spend=0,
            dice_pool=dice_pool,
        )
        try:
            resolution, _event = rpg_service.resolve_action(request)
            summary = self._format_result(resolution)
            self._store_result(summary)
            reaction = self.apply_world_reaction(resolution)
            self.run_proposal_pipeline(resolution, campaign_id)
            self._post_message(
                "system",
                format_mechanical_bubble(actor_name, action_key, resolution, reaction),
            )
            if session.dungeon is not None and session.state is not None:
                room = session.current_room()
                if room is None:
                    self._post_message("system", "Select a room to get DM narration.")
                else:
                    outcome = resolution.outcome.upper()
                    msg = (
                        f"{actor_name} [{action_key.upper()}] {intent or '(no intent)'}"
                        f" — {outcome}"
                    )
                    self._get_narration().request_narration(msg)
            self._refresh_right_panel(actor_id)
        except Exception:
            _log.exception("_run_chat_action failed")

    def on_resolve_action(
        self,
        campaign_id: str,
        actor_id: str,
        intent: str,
        action_key: str,
        push_yourself: bool,
        momentum_spend: int,
        dice_pool: int,
    ) -> None:
        session = self._session
        rpg_service = self._get_rpg_service()
        if rpg_service is None:
            return
        request = self._build_request(
            campaign_id=campaign_id,
            actor_id=actor_id,
            intent=intent,
            action_key=action_key,
            push_yourself=push_yourself,
            momentum_spend=momentum_spend,
            dice_pool=dice_pool,
        )
        try:
            resolution, _event = rpg_service.resolve_action(request)
            summary = self._format_result(resolution)
            self._store_result(summary)
            self.apply_world_reaction(resolution)
            self.run_proposal_pipeline(resolution, campaign_id)
            if session.dungeon is not None and session.state is not None:
                room = session.current_room()
                if room is None:
                    self._post_message("system", "Select a room to get DM narration.")
                else:
                    outcome = summary.get("outcome", "?").upper()
                    dice = summary.get("dice", [])
                    actor_name = next(
                        (a.display_name for a in session.actors if a.actor_id == actor_id),
                        actor_id,
                    )
                    msg = (
                        f"{actor_name} [{action_key.upper()}] {intent or '(no intent)'}"
                        f" — {outcome}  dice={dice}"
                    )
                    self._get_narration().request_narration(msg)
            self._refresh_right_panel(actor_id)
        except Exception:
            _log.exception("resolve_action failed")

    # -- skill-roll path ---------------------------------------------------------

    def resolve_vna_roll(self, card: ActionCard, actor: ActorState) -> None:
        """Resolve a skill-verb Card as an action roll and narrate the outcome."""
        from dungeon_daddy.rpg.action_resolution import resolve_card_roll
        from dungeon_daddy.ui.mechanical_bubble import format_mechanical_bubble

        session = self._session
        rpg_service = self._get_rpg_service()
        if rpg_service is None or session.state is None:
            return
        campaign_id = session.campaign_id or session.state.dungeon_id
        card_roll = resolve_card_roll(
            card,
            campaign_id=campaign_id,
            actor={"actor_id": actor.actor_id, "actions": actor.actions},
        )
        resolution = card_roll.resolution
        # Resolve the acted-upon object once and share it: the obstacle check
        # reads its (pre-resolution) contested transitions, and the world
        # reaction reads its state-independent policy + bindings.
        acted_object = self.resolve_acted_object(card.noun_id)
        obstacle = self.maybe_resolve_obstacle(
            card, actor, resolution.outcome, acted_object=acted_object
        )
        reaction = self.apply_world_reaction(resolution, acted_object=acted_object)
        self.run_proposal_pipeline(resolution, campaign_id)
        self._post_message(
            "system",
            format_mechanical_bubble(actor.display_name, card.verb, resolution, reaction),
        )
        if session.dungeon is not None and session.state.current_room_id:
            room = session.current_room()
            if room is not None:
                noun_label = self._noun_label_for(card.noun_id) or card.noun_id
                msg = (
                    f"{actor.display_name} [{card.verb.upper()}] {noun_label}"
                    f" ({card.adverb}) — {resolution.outcome.upper()}"
                )
                if obstacle is not None:
                    t = obstacle.transition
                    msg += f" [{noun_label}: {t.from_state} → {t.to_state}]"
                    if obstacle.complication:
                        msg += " (resolved, but with a complication)"
                self._get_narration().request_narration(msg)
        self._refresh_right_panel(actor.actor_id)

    def _noun_label_for(self, noun_id: str) -> str | None:
        """Human-readable label for an offered noun id (for narration/messages)."""
        return next(
            (n.label for n in self._get_nouns() if n.noun_id == noun_id), None
        )

    def resolve_acted_object(self, noun_id: str) -> RoomObject | None:
        """Resolve a card's noun to its :class:`RoomObject`, or ``None``.

        Phase 51.6 Slice 8: only room *objects* carry a ``reaction_policy`` +
        scripted ``reaction_bindings``, so the world-reaction engine can branch
        on them. Item/actor/exit nouns (and anything unknown) return ``None`` —
        the reaction then falls to the ambient rule.
        """
        repo = self._session.mem_repo
        if repo is None:
            return None
        obj_dict = repo.get_room_object(noun_id)
        if obj_dict is None:
            return None
        from dungeon_daddy.rpg.models import RoomObject
        return RoomObject(**obj_dict)

    def maybe_resolve_obstacle(
        self,
        card: ActionCard,
        actor: ActorState,
        outcome: Outcome,
        acted_object: RoomObject | None = None,
    ) -> ObstacleRollResolution | None:
        """Apply a successful contested-approach roll to the target's state (Phase 51.5 Part A).

        When ``card.verb`` matches one of the target object's contested approaches
        and ``outcome`` resolves it (crit/full clean, partial with a complication;
        miss fails — locked mapping), route the matched transition through the
        deterministic ``ActivateObject`` pipeline so its state change + side-effects
        apply and objectives re-advance. Returns the
        :class:`ObstacleRollResolution` applied, or ``None`` if nothing changed.

        ``acted_object`` is the pre-resolved target (shared with the world
        reaction to avoid a second fetch); it is re-resolved from ``card.noun_id``
        when the caller does not supply it.
        """
        from dungeon_daddy.rpg.command import ActivateObject
        from dungeon_daddy.rpg.obstacles import resolve_obstacle_with_roll

        if self._session.mem_repo is None or self._session.campaign_id is None:
            return None
        obj = acted_object if acted_object is not None else self.resolve_acted_object(card.noun_id)
        if obj is None:
            return None
        resolved = resolve_obstacle_with_roll(obj, verb=card.verb, outcome=outcome)
        if resolved is None:
            return None
        command = ActivateObject(
            actor_id=actor.actor_id,
            object_id=card.noun_id,
            trigger=resolved.transition.trigger,
        )
        if self.apply_vna_command(command):
            return resolved
        return None

    # -- world reaction (via Slice 1's ReactionApplier) --------------------------

    def apply_world_reaction(
        self, resolution: ActionResolution, acted_object: RoomObject | None = None
    ) -> WorldReaction | None:
        """Compute + atomically persist the action's world reaction (Slice 1).

        The applier reads the session/clocks/stress from the shared context,
        persists the clock + stress writes atomically, and posts a system line
        if the reaction cannot be fully applied.
        """
        from dungeon_daddy.play.reaction_applier import ReactionApplier

        debug = self._get_debug()
        applier = ReactionApplier(
            self._session,
            self._get_rpg_service(),
            post_system=lambda text: self._post_message("system", text),
            on_reaction=(debug.set_reaction if debug is not None else None),
        )
        return applier.apply(resolution, acted_object)

    # -- proposal pipeline (LLM world-reaction proposals) -------------------------

    def run_proposal_pipeline(self, resolution: ActionResolution, campaign_id: str) -> None:
        from dungeon_daddy.rpg.actor_control import filter_player_actors
        from dungeon_daddy.rpg.proposal import parse_proposal
        from dungeon_daddy.rpg.proposal_applier import (
            ApplyResult,
            apply_low_risk_proposals,
        )
        from dungeon_daddy.rpg.proposal_validator import (
            ValidationResult,
            validate_proposal,
        )

        session = self._session
        dm_agent = self._get_dm_agent()
        debug = self._get_debug()
        repo = session.mem_repo
        if dm_agent is None or repo is None or debug is None:
            return
        raw_clocks = repo.get_clocks(campaign_id)
        known_clocks = [
            {"clock_id": r["clock_id"], "label": r["label"],
             "filled": r["filled"], "segments": r["segments"]}
            for r in raw_clocks
        ]
        known_clock_ids = [c["clock_id"] for c in known_clocks]
        all_actors = session.actors
        known_actors = [{"actor_id": a.actor_id, "display_name": a.display_name} for a in all_actors]
        known_actor_ids = [a["actor_id"] for a in known_actors]
        player_actor_ids = [a.actor_id for a in filter_player_actors(all_actors)]

        room_name = ""
        room_note = ""
        room = self._session.current_room()
        if room is not None:
            room_name = room.name
            room_note = room.note or ""

        raw = dm_agent.request_proposal(
            resolution=resolution,
            context_bundle=None,
            known_clocks=known_clocks,
            known_actors=known_actors,
            player_actor_ids=player_actor_ids,
            room_name=room_name,
            room_note=room_note,
        )
        proposal = parse_proposal(raw)
        if proposal is not None:
            validation_result = validate_proposal(
                proposal,
                known_clock_ids=set(known_clock_ids),
                known_actor_ids=set(known_actor_ids),
                player_actor_ids=set(player_actor_ids),
                obstacle_resolved_states=self.obstacle_resolved_states(campaign_id),
            )
            apply_result = apply_low_risk_proposals(
                validation_result,
                repo,
                campaign_id,
                action_key=resolution.action_key,
                intent=resolution.intent,
            )
            # A validated ResolveObstacleChange is applied through the deterministic
            # ActivateObject seam (not apply_low_risk_proposals, which skips it), gated
            # on a resolving roll outcome — the constrained Part B object-state authority.
            actor_id = player_actor_ids[0] if player_actor_ids else (
                known_actor_ids[0] if known_actor_ids else None
            )
            self.apply_obstacle_proposals(validation_result, resolution.outcome, actor_id)
        else:
            validation_result = ValidationResult()
            apply_result = ApplyResult()
        debug.set_proposal_result(validation_result, apply_result)

    def obstacle_resolved_states(self, campaign_id: str) -> dict[str, str]:
        """Map ``{obstacle slug: authored resolved state}`` for the current room.

        Bounds the DM-ruled ResolveObstacleChange authority to obstacles present in
        the party's room, each only to its single canonical resolved state.
        """
        from dungeon_daddy.rpg.models import RoomObject
        from dungeon_daddy.rpg.obstacles import obstacle_resolved_state

        repo = self._session.mem_repo
        state = self._session.state
        if repo is None or state is None or not state.current_room_id:
            return {}
        states: dict[str, str] = {}
        for od in repo.get_objects_by_room(campaign_id, state.current_room_id):
            resolved = obstacle_resolved_state(RoomObject(**od))
            if resolved is not None:
                states[od["slug"]] = resolved
        return states

    def apply_obstacle_proposals(
        self,
        validation_result: ValidationResult,
        outcome: Outcome,
        actor_id: str | None,
    ) -> None:
        """Apply accepted DM-ruled obstacle resolutions (Phase 51.5 Part B Slice 6).

        For each accepted :class:`ResolveObstacleChange`, on a resolving roll outcome
        (locked mapping), route the obstacle to its authored resolved state through
        the deterministic ``ActivateObject`` pipeline so ``update_object_state`` +
        side-effects fire and objectives re-advance. The validator already guarantees
        ``to_state`` is the obstacle's authored resolved state.
        """
        from dungeon_daddy.rpg.command import ActivateObject
        from dungeon_daddy.rpg.models import RoomObject
        from dungeon_daddy.rpg.obstacles import is_resolving_outcome, resolving_trigger
        from dungeon_daddy.rpg.proposal import ResolveObstacleChange

        repo = self._session.mem_repo
        state = self._session.state
        if repo is None or actor_id is None or state is None:
            return
        if not is_resolving_outcome(outcome):
            return
        room_id = state.current_room_id
        if not room_id:
            return
        campaign_id = self._session.campaign_id
        if campaign_id is None:
            return
        by_slug = {
            od["slug"]: RoomObject(**od)
            for od in repo.get_objects_by_room(campaign_id, room_id)
        }
        for change in validation_result.accepted:
            if not isinstance(change, ResolveObstacleChange):
                continue
            obj = by_slug.get(change.object_slug)
            if obj is None:
                continue
            trigger = resolving_trigger(obj, change.to_state)
            if trigger is None:
                continue
            self.apply_vna_command(
                ActivateObject(
                    actor_id=actor_id, object_id=obj.object_id, trigger=trigger,
                )
            )

    # -- objective advancement (Phase 51.5 §7.9) ------------------------------

    def advance_objectives(self) -> None:
        """Re-evaluate active objectives after a world-state mutation (§7.9).

        A subsystem reaching its required state completes the tier's objective,
        ticking the latching intimacy clock (the single tick source, D5) and
        activating the next tier. Each completion surfaces a dungeon line.
        """
        from dungeon_daddy.rpg.objectives import advance_objectives

        repo = self._session.mem_repo
        campaign_id = self._session.campaign_id
        if repo is None or campaign_id is None:
            return
        for _ in advance_objectives(repo, campaign_id):
            self._post_message(
                "dungeon", "◆ The Crucible stirs — its bond with you deepens."
            )
