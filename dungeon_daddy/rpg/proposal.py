"""LLM reaction proposal models — Phase 36."""
from __future__ import annotations

import json
import logging
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, ValidationError

_log = logging.getLogger(__name__)


class AdvanceClockChange(BaseModel):
    kind: Literal["advance_clock"] = "advance_clock"
    clock_id: str
    amount: int
    reason: str


class ApplyConsequenceChange(BaseModel):
    kind: Literal["apply_consequence"] = "apply_consequence"
    actor_id: str
    track_key: str
    amount: int
    reason: str


class CreateMemoryChange(BaseModel):
    kind: Literal["create_memory"] = "create_memory"
    title: str
    summary: str
    importance: int
    tags: list[str]


class NpcReactionChange(BaseModel):
    kind: Literal["npc_reaction"] = "npc_reaction"
    npc_id: str
    reaction: str
    reason: str


ProposedChange = Annotated[
    Union[AdvanceClockChange, ApplyConsequenceChange, CreateMemoryChange, NpcReactionChange],
    Field(discriminator="kind"),
]


class LLMReactionProposal(BaseModel):
    narration_hint: str
    proposed_changes: list[ProposedChange]
    source: Literal["deterministic", "llm_draft", "human_approved"] = "llm_draft"


def parse_proposal(raw: str) -> LLMReactionProposal | None:
    """Parse LLM JSON string into a proposal; return None on any error."""
    try:
        data = json.loads(raw)
        return LLMReactionProposal.model_validate(data)
    except (json.JSONDecodeError, ValidationError, Exception) as exc:
        _log.warning("parse_proposal failed: %s", exc)
        return None
