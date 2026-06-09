from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.rpg.models import ActorState

CHIP_ORDER: list[str] = [
    "fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"
]


@dataclass
class ActionChipData:
    action_key: str
    label: str
    rating: int | None


def build_action_chips(actor: ActorState | None) -> list[ActionChipData]:
    actions = actor.actions if actor is not None else {}
    return [
        ActionChipData(
            action_key=key,
            label=key.upper(),
            rating=actions[key] if actions.get(key) else None,
        )
        for key in CHIP_ORDER
    ]
