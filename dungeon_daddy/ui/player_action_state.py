from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dungeon_daddy.rpg.intent import PendingIntent

ACTION_KEYS: frozenset[str] = frozenset(
    {"fight", "move", "endure", "tinker", "study", "focus", "sense", "sway", "channel"}
)


@dataclass
class PlayerActionState:
    actor_id: str | None = None
    action_key: str | None = None
    intent: str = ""
    awaiting_confirmation: bool = False
    resolution_summary: str | None = None
    pending_intent: "PendingIntent | None" = None
    _actor_roster: list[str] = field(default_factory=list)
    _roster_index: int = 0

    @property
    def has_multiple_actors(self) -> bool:
        return len(self._actor_roster) > 1

    def set_actor_roster(self, actor_ids: list[str]) -> None:
        self._actor_roster = list(actor_ids)
        self._roster_index = 0
        self.actor_id = actor_ids[0] if actor_ids else None

    def select_next_actor(self) -> None:
        if len(self._actor_roster) < 2:
            return
        self._roster_index = (self._roster_index + 1) % len(self._actor_roster)
        self.actor_id = self._actor_roster[self._roster_index]

    def select_prev_actor(self) -> None:
        if len(self._actor_roster) < 2:
            return
        self._roster_index = (self._roster_index - 1) % len(self._actor_roster)
        self.actor_id = self._actor_roster[self._roster_index]

    def select_actor(self, actor_id: str | None) -> None:
        self.actor_id = actor_id

    def select_action(self, action_key: str | None) -> None:
        if action_key is not None and action_key not in ACTION_KEYS:
            raise ValueError(f"Unknown action key: {action_key!r}")
        self.action_key = action_key

    def set_intent(self, text: str) -> None:
        self.intent = text

    def set_awaiting_confirmation(self, flag: bool) -> None:
        self.awaiting_confirmation = flag

    def set_resolution_summary(self, summary: str | None) -> None:
        self.resolution_summary = summary

    def set_pending_intent(self, pi: "PendingIntent | None") -> None:
        self.pending_intent = pi

    def reset(self) -> None:
        self.action_key = None
        self.intent = ""
        self.awaiting_confirmation = False
        self.resolution_summary = None
        self.pending_intent = None
