from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PendingIntent(BaseModel):
    actor_id: str
    raw_text: str
    suggested_action_keys: list[str] = Field(default_factory=list)
    suggested_primary_action: str | None = None
    stakes_text: str = ""
    status: Literal["awaiting_confirmation", "resolved", "cancelled"] = "awaiting_confirmation"
