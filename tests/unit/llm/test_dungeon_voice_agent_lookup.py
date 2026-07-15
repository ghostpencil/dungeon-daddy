"""Slice B4c — DungeonVoiceAgent `lookup_world` seam (spec §9/§10).

Mirror of the DM-agent seam: when the provider ``supports_tools`` and a
``lookup`` executor is injected, ``respond`` runs the agent-owned tool loop with
``LOOKUP_WORLD_TOOL`` + scoped guidance; otherwise today's ``complete`` path.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.llm.agents.dungeon_voice_agent import DungeonVoiceAgent
from dungeon_daddy.llm.lookup_tool import LOOKUP_WORLD_TOOL
from dungeon_daddy.llm.provider import (
    LLMMessage,
    LLMRoundResult,
    LLMToolCall,
    LLMToolDef,
)


@dataclass
class _RoundCall:
    messages: list[LLMMessage]
    system: str
    tools: list[LLMToolDef] | None
    max_tokens: int


@dataclass
class _ToolProvider:
    scripted: list[LLMRoundResult] = field(default_factory=list)
    complete_response: str = "plain voice"
    supports_tools: bool = True
    round_calls: list[_RoundCall] = field(default_factory=list)
    complete_calls: int = 0

    def complete(self, messages, system="", max_tokens=1024, response_format=None):  # type: ignore[no-untyped-def]
        self.complete_calls += 1
        return self.complete_response

    def complete_round(
        self,
        messages: list[LLMMessage],
        system: str = "",
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 1024,
    ) -> LLMRoundResult:
        self.round_calls.append(_RoundCall(list(messages), system, tools, max_tokens))
        return self.scripted[len(self.round_calls) - 1]

    @property
    def model_id(self) -> str:
        return "mock"


def _respond(agent: DungeonVoiceAgent, **kw: object) -> str:
    return agent.respond(
        dungeon_voice="I am the deep dark.",
        intimacy_filled=1,
        intimacy_segments=4,
        dungeon_knowledge=["The core hums."],
        player_message="Tell me about Mira.",
        actor="Kira",
        **kw,  # type: ignore[arg-type]
    )


def test_respond_uses_tool_loop_when_lookup_injected() -> None:
    provider = _ToolProvider(
        scripted=[
            LLMRoundResult(tool_calls=[LLMToolCall("c1", "lookup_world", {"query": "mira"})]),
            LLMRoundResult(text="Mira? She walked my halls an age ago."),
        ]
    )
    seen: list[LLMToolCall] = []
    agent = DungeonVoiceAgent(provider)

    out = _respond(agent, lookup=lambda call: seen.append(call) or "rows: mira")

    assert out == "Mira? She walked my halls an age ago."
    assert [c.name for c in seen] == ["lookup_world"]
    assert provider.round_calls[0].tools == [LOOKUP_WORLD_TOOL]
    assert "lookup_world" in provider.round_calls[0].system
    assert provider.complete_calls == 0


def test_respond_without_lookup_uses_complete() -> None:
    provider = _ToolProvider(complete_response="plain voice")
    agent = DungeonVoiceAgent(provider)

    out = _respond(agent)

    assert out == "plain voice"
    assert provider.round_calls == []
    assert provider.complete_calls == 1


@dataclass
class _PlainProvider:
    """A provider from before the tool era — no ``complete_round``, no
    ``supports_tools`` (the `AnthropicProvider` shape; spec §9 defers it)."""

    complete_response: str = "plain voice"
    complete_calls: int = 0

    def complete(self, messages, system="", max_tokens=1024, response_format=None):  # type: ignore[no-untyped-def]
        self.complete_calls += 1
        return self.complete_response

    @property
    def model_id(self) -> str:
        return "plain"


def test_respond_falls_back_to_complete_when_provider_lacks_tool_support() -> None:
    """The `supports_tools` guard is load-bearing (Slice B4 review fix):
    `DialogueCoordinator` injects `lookup` without consulting the provider, so
    only this guard prevents an `AttributeError` on every voice turn."""
    provider = _PlainProvider()
    agent = DungeonVoiceAgent(provider)  # type: ignore[arg-type]

    out = _respond(agent, lookup=lambda call: "rows: mira")

    assert out == "plain voice"
    assert provider.complete_calls == 1


def test_respond_falls_back_to_complete_when_tools_unsupported() -> None:
    provider = _ToolProvider(complete_response="plain voice", supports_tools=False)
    agent = DungeonVoiceAgent(provider)

    out = _respond(agent, lookup=lambda call: "rows: mira")

    assert out == "plain voice"
    assert provider.round_calls == []
    assert provider.complete_calls == 1
