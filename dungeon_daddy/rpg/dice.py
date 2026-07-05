from __future__ import annotations

import random
from typing import Literal

from pydantic import BaseModel

Outcome = Literal["critical", "full", "partial", "miss"]


class DiceResult(BaseModel):
    dice: list[int]
    highest: int
    outcome: Outcome


def _classify(highest: int, dice: list[int]) -> Outcome:
    if highest >= 6 and dice.count(6) >= 2:
        return "critical"
    if highest == 6:
        return "full"
    if highest >= 4:
        return "partial"
    return "miss"


def roll_pool(pool: int, fixed: list[int] | None = None) -> DiceResult:
    if pool < 1:
        pool = 1
    dice = fixed[:pool] if fixed is not None else [random.randint(1, 6) for _ in range(pool)]
    highest = max(dice)
    return DiceResult(dice=dice, highest=highest, outcome=_classify(highest, dice))
