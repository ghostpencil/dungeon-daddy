"""Slice B4b — DungeonMasterAgent `lookup_world` seam (spec §9/§10).

When the provider ``supports_tools`` and a ``lookup`` executor is injected,
``respond`` runs the agent-owned tool loop (offering ``LOOKUP_WORLD_TOOL`` and a
scoped "when to look things up" prompt section); otherwise it uses exactly
today's single-shot ``complete`` path. Fake providers at the DI seam (TESTING.md
§2) — no live API.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room
from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
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
    """Tool-capable fake: scripts ``complete_round`` and records both seams."""

    scripted: list[LLMRoundResult] = field(default_factory=list)
    complete_response: str = "plain narration"
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


def _room() -> Room:
    return Room(id="1-A", num=1, name="Entry Hall", x=0, y=0, w=3, h=3, type="hall", note="")


def _level() -> Level:
    return Level(
        id=1, name="Vestibule", summary="", ecology="", loop="lock_key",
        width=12, height=10, entries=[], rooms=[_room()], connections=[],
    )


def _dungeon() -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(
            title="Tomb", theme="Undead", setting="A tomb.",
            party="4 level 3", quest="Recover the Crown.",
        ),
        levels=[_level()],
    )


def test_respond_uses_tool_loop_when_lookup_injected() -> None:
    provider = _ToolProvider(
        scripted=[
            LLMRoundResult(tool_calls=[LLMToolCall("c1", "lookup_world", {"query": "mira"})]),
            LLMRoundResult(text="Mira is an off-scene NPC far to the north."),
        ]
    )
    seen: list[LLMToolCall] = []
    agent = DungeonMasterAgent(provider)

    out = agent.respond(
        history=[LLMMessage(role="user", content="who is mira?")],
        room=_room(), level=_level(), dungeon=_dungeon(),
        lookup=lambda call: seen.append(call) or "rows: mira-coldwell",
    )

    assert out == "Mira is an off-scene NPC far to the north."
    assert [c.name for c in seen] == ["lookup_world"]
    assert provider.round_calls[0].tools == [LOOKUP_WORLD_TOOL]
    assert provider.complete_calls == 0


def test_tool_path_adds_scoped_lookup_guidance_to_system() -> None:
    provider = _ToolProvider(scripted=[LLMRoundResult(text="answer")])
    agent = DungeonMasterAgent(provider)

    agent.respond(
        history=[LLMMessage(role="user", content="hi")],
        room=_room(), level=_level(), dungeon=_dungeon(),
        lookup=lambda call: "rows",
    )

    assert "lookup_world" in provider.round_calls[0].system


def test_respond_without_lookup_uses_complete_even_if_tools_supported() -> None:
    provider = _ToolProvider(complete_response="plain narration")
    agent = DungeonMasterAgent(provider)

    out = agent.respond(
        history=[LLMMessage(role="user", content="hi")],
        room=_room(), level=_level(), dungeon=_dungeon(),
    )

    assert out == "plain narration"
    assert provider.round_calls == []
    assert provider.complete_calls == 1


@dataclass
class _PlainProvider:
    """A provider from before the tool era — no ``complete_round``, no
    ``supports_tools``. `AnthropicProvider` is exactly this shape (spec §9
    defers its tool support)."""

    complete_response: str = "plain narration"
    complete_calls: int = 0

    def complete(self, messages, system="", max_tokens=1024, response_format=None):  # type: ignore[no-untyped-def]
        self.complete_calls += 1
        return self.complete_response

    @property
    def model_id(self) -> str:
        return "plain"


def test_respond_falls_back_to_complete_when_provider_lacks_tool_support() -> None:
    """The `supports_tools` guard is load-bearing (Slice B4 review fix).

    Both coordinators inject `lookup` whenever a repo exists — they do not check
    the provider. So this guard is the only thing standing between a non-tool
    provider and an `AttributeError` on *every* narration turn.
    """
    provider = _PlainProvider()
    agent = DungeonMasterAgent(provider)  # type: ignore[arg-type]

    out = agent.respond(
        history=[LLMMessage(role="user", content="who is mira?")],
        room=_room(), level=_level(), dungeon=_dungeon(),
        lookup=lambda call: "rows: mira-coldwell",
    )

    assert out == "plain narration"
    assert provider.complete_calls == 1


def test_respond_falls_back_to_complete_when_tools_unsupported() -> None:
    # The capability is declared but false — the tool loop must stay off.
    provider = _ToolProvider(complete_response="plain narration", supports_tools=False)
    agent = DungeonMasterAgent(provider)

    out = agent.respond(
        history=[LLMMessage(role="user", content="who is mira?")],
        room=_room(), level=_level(), dungeon=_dungeon(),
        lookup=lambda call: "rows: mira-coldwell",
    )

    assert out == "plain narration"
    assert provider.round_calls == []
    assert provider.complete_calls == 1
