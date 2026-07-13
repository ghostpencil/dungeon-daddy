"""Unit tests for the agent-owned tool loop (``llm/tool_loop.py``, spec §9).

The provider is pure transport (``complete_round``); the loop lives here. A
``_FakeProvider`` scripts a queue of ``LLMRoundResult`` and records every
``complete_round`` call so the tests can assert the request→tool→request cycle
without a live API.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.llm.provider import (
    LLMMessage,
    LLMRoundResult,
    LLMToolCall,
    LLMToolDef,
)
from dungeon_daddy.llm.tool_loop import run_tool_loop


@dataclass
class _Call:
    messages: list[LLMMessage]
    system: str
    tools: list[LLMToolDef] | None
    max_tokens: int


@dataclass
class _FakeProvider:
    """Scripts ``complete_round`` results and records the calls it received."""

    scripted: list[LLMRoundResult]
    calls: list[_Call] = field(default_factory=list)
    supports_tools: bool = True

    def complete_round(
        self,
        messages: list[LLMMessage],
        system: str = "",
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 1024,
    ) -> LLMRoundResult:
        # Snapshot the messages list so later mutation doesn't rewrite history.
        self.calls.append(_Call(list(messages), system, tools, max_tokens))
        return self.scripted[len(self.calls) - 1]


_TOOL = LLMToolDef(name="lookup_world", description="search", parameters={})


def _lookup_tool_call(query: str = "mira") -> LLMToolCall:
    return LLMToolCall(call_id="c1", name="lookup_world", arguments={"query": query})


def test_plain_answer_returns_directly_without_calling_executor() -> None:
    provider = _FakeProvider(scripted=[LLMRoundResult(text="the answer")])
    executor_calls: list[LLMToolCall] = []

    result = run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="hi")],
        system="sys",
        tools=[_TOOL],
        executor=lambda call: executor_calls.append(call) or "unused",
    )

    assert result == "the answer"
    assert executor_calls == []
    assert len(provider.calls) == 1


def test_tool_call_runs_executor_then_returns_forced_answer() -> None:
    provider = _FakeProvider(
        scripted=[
            LLMRoundResult(tool_calls=[_lookup_tool_call()]),
            LLMRoundResult(text="mira is an off-scene NPC"),
        ]
    )
    executor_calls: list[LLMToolCall] = []

    def executor(call: LLMToolCall) -> str:
        executor_calls.append(call)
        return "rows: mira-coldwell"

    result = run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="who is mira?")],
        system="sys",
        tools=[_TOOL],
        executor=executor,
    )

    assert result == "mira is an off-scene NPC"
    assert [c.name for c in executor_calls] == ["lookup_world"]
    assert len(provider.calls) == 2


def test_resubmitted_history_carries_tool_call_and_result_messages() -> None:
    call = _lookup_tool_call()
    provider = _FakeProvider(
        scripted=[
            LLMRoundResult(text="thinking", tool_calls=[call]),
            LLMRoundResult(text="done"),
        ]
    )

    run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="who is mira?")],
        system="sys",
        tools=[_TOOL],
        executor=lambda c: "rows: mira-coldwell",
    )

    resubmitted = provider.calls[1].messages
    assert [m.role for m in resubmitted] == ["user", "assistant", "tool"]
    assistant_msg = resubmitted[1]
    assert assistant_msg.content == "thinking"
    assert assistant_msg.tool_calls == [call]
    tool_msg = resubmitted[2]
    assert tool_msg.content == "rows: mira-coldwell"
    assert tool_msg.tool_call_id == "c1"


def test_final_round_is_forced_plain_without_tools() -> None:
    provider = _FakeProvider(
        scripted=[
            LLMRoundResult(tool_calls=[_lookup_tool_call()]),
            LLMRoundResult(text="done"),
        ]
    )

    run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="q")],
        system="sys",
        tools=[_TOOL],
        executor=lambda c: "rows",
    )

    assert provider.calls[0].tools == [_TOOL]
    assert provider.calls[1].tools is None


def test_multiple_tool_calls_in_one_round_each_run_and_appended() -> None:
    calls = [
        LLMToolCall(call_id="a", name="lookup_world", arguments={"query": "x"}),
        LLMToolCall(call_id="b", name="lookup_world", arguments={"tags": ["theme:guilt"]}),
    ]
    provider = _FakeProvider(
        scripted=[LLMRoundResult(tool_calls=calls), LLMRoundResult(text="done")]
    )
    seen: list[str] = []

    run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="q")],
        system="sys",
        tools=[_TOOL],
        executor=lambda c: seen.append(c.call_id) or f"rows for {c.call_id}",
    )

    assert seen == ["a", "b"]
    resubmitted = provider.calls[1].messages
    tool_msgs = [m for m in resubmitted if m.role == "tool"]
    assert [m.tool_call_id for m in tool_msgs] == ["a", "b"]
    assert [m.content for m in tool_msgs] == ["rows for a", "rows for b"]


def test_executor_exception_becomes_error_string_and_loop_continues() -> None:
    provider = _FakeProvider(
        scripted=[
            LLMRoundResult(tool_calls=[_lookup_tool_call()]),
            LLMRoundResult(text="recovered"),
        ]
    )

    def boom(call: LLMToolCall) -> str:
        raise RuntimeError("db locked")

    result = run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="q")],
        system="sys",
        tools=[_TOOL],
        executor=boom,
    )

    assert result == "recovered"
    tool_msg = [m for m in provider.calls[1].messages if m.role == "tool"][0]
    assert "db locked" in tool_msg.content


def test_none_text_on_final_round_returns_empty_string() -> None:
    provider = _FakeProvider(scripted=[LLMRoundResult(text=None)])

    result = run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="q")],
        system="sys",
        tools=[_TOOL],
        executor=lambda c: "rows",
    )

    assert result == ""


def test_final_round_returns_text_even_if_provider_still_emits_tool_calls() -> None:
    # tools=None on the last round should mean tool_calls are never processed:
    # a non-conformant provider that still returns them must not blank the answer
    # or re-run the executor.
    provider = _FakeProvider(
        scripted=[
            LLMRoundResult(text="t0", tool_calls=[_lookup_tool_call()]),
            LLMRoundResult(text="forced answer", tool_calls=[_lookup_tool_call()]),
        ]
    )
    executor_calls: list[LLMToolCall] = []

    result = run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="q")],
        system="sys",
        tools=[_TOOL],
        executor=lambda c: executor_calls.append(c) or "rows",
    )

    assert result == "forced answer"
    assert len(executor_calls) == 1  # only the first (tool-offering) round ran it


def test_max_rounds_below_one_still_makes_one_provider_call() -> None:
    provider = _FakeProvider(scripted=[LLMRoundResult(text="answer")])

    result = run_tool_loop(
        provider,
        messages=[LLMMessage(role="user", content="q")],
        system="sys",
        tools=[_TOOL],
        executor=lambda c: "rows",
        max_rounds=0,
    )

    assert result == "answer"
    assert len(provider.calls) == 1
    assert provider.calls[0].tools is None  # clamped to a single forced-plain round
