"""Agent-owned tool loop (spec §9, L3).

The provider is pure transport: ``complete_round`` sends tools and returns
*either* text or tool-call requests. The request→tool→request cycle lives
here, written once, so no agent reimplements it.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from .provider import LLMMessage, LLMProvider, LLMToolCall, LLMToolDef

_log = logging.getLogger(__name__)


def run_tool_loop(
    provider: LLMProvider,
    messages: list[LLMMessage],
    system: str = "",
    tools: list[LLMToolDef] | None = None,
    *,
    executor: Callable[[LLMToolCall], str],
    max_rounds: int = 2,
    max_tokens: int = 1024,
) -> str:
    """Run the model until it answers in plain text (spec §9).

    Each round calls ``complete_round``; a round that returns ``tool_calls`` runs
    ``executor`` per call, appends the results, and resubmits. The final round
    resubmits **without** ``tools`` to force a plain answer (L4: the model must
    answer with what it has once the round budget is spent).
    """
    history = list(messages)
    rounds = max(1, max_rounds)  # always make at least one (forced-plain) round
    for round_index in range(rounds):
        is_last = round_index == rounds - 1
        result = provider.complete_round(
            history,
            system,
            tools=None if is_last else tools,
            max_tokens=max_tokens,
        )
        # The last round is forced plain (tools=None); return its text without
        # processing any tool calls a non-conformant provider might still emit.
        if is_last or not result.tool_calls:
            return result.text or ""
        history.append(
            LLMMessage(
                role="assistant",
                content=result.text or "",
                tool_calls=result.tool_calls,
            )
        )
        for call in result.tool_calls:
            output = _run_executor(executor, call)
            history.append(
                LLMMessage(role="tool", content=output, tool_call_id=call.call_id)
            )
    return ""


def _run_executor(
    executor: Callable[[LLMToolCall], str], call: LLMToolCall
) -> str:
    """Run one tool call, returning its output. A raised exception is returned
    to the model as an error string rather than propagated (L4: tool errors
    never raise through the turn) — and logged, because L4 keeps the error from
    killing the turn, not from being seen."""
    try:
        return executor(call)
    except Exception as exc:  # noqa: BLE001 — returned to the model AND logged
        _log.exception("tool %r failed: args=%r", call.name, call.arguments)
        return f"Error: {exc}"
