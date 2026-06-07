from __future__ import annotations

import uuid

from dungeon_daddy.rpg.dice import roll_pool
from dungeon_daddy.rpg.models import ActionRequest, ActionResolution


def resolve_action(
    request: ActionRequest,
    fixed: list[int] | None = None,
) -> ActionResolution:
    push_die = 1 if request.push_yourself else 0
    total_pool = request.dice_pool + request.momentum_spend + push_die
    result = roll_pool(pool=total_pool, fixed=fixed)
    return ActionResolution(
        resolution_id=str(uuid.uuid4()),
        campaign_id=request.campaign_id,
        actor_id=request.actor_id,
        action_key=request.action_key,
        dice_rolled=result.dice,
        outcome=result.outcome,
        stress_cost=push_die,
        intent=request.intent,
    )
