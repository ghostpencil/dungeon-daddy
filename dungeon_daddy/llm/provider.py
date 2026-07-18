"""Core LLM types: LLMMessage, LLMProvider Protocol, LLMError."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeGuard, runtime_checkable


@dataclass
class LLMToolDef:
    """A tool the model may call. ``parameters`` is a JSON Schema; providers
    translate it to their native tool format."""
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class LLMToolCall:
    """A model-requested tool invocation, decoded to a provider-neutral shape."""
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMRoundResult:
    """One round of ``complete_round``: either plain text (``text`` set) or a
    request to run tools (``tool_calls`` non-empty)."""
    text: str | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)


@dataclass
class LLMMessage:
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_call_id: str | None = None
    tool_calls: list[LLMToolCall] | None = None


class LLMError(Exception):
    """
    Raised by any LLMProvider implementation on API, network, or auth failure.
    Callers catch LLMError; they do not catch provider-specific exceptions.
    """


@runtime_checkable
class LLMProvider(Protocol):
    """
    Synchronous LLM provider interface.
    All implementations must be safe to call from a background thread.
    Tool-round transport is NOT part of this base contract — it lives in
    ``ToolCapableProvider``, so a plain-completion provider (e.g.
    ``AnthropicProvider``) satisfies this Protocol without it.
    """

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> str: ...

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]: ...

    @property
    def model_id(self) -> str: ...

    @property
    def last_usage(self) -> tuple[int, int] | None: ...


@runtime_checkable
class ToolCapableProvider(Protocol):
    """The tool-round transport seam (spec §9 L3): exactly what the agent-owned
    tool loop needs, kept separate from ``LLMProvider`` so tool capability is
    detected by ``isinstance`` narrowing instead of ``getattr`` probing.
    Production providers that support tools implement both Protocols."""

    def complete_round(
        self,
        messages: list[LLMMessage],
        system: str = "",
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 1024,
    ) -> LLMRoundResult:
        """One tool-use round: returns model text OR tool-call requests.
        The request→tool→request loop lives in the agent layer (``llm/tool_loop.py``),
        not on the provider (spec §9 L3)."""
        ...

    @property
    def supports_tools(self) -> bool: ...


def provider_supports_tools(provider: object) -> TypeGuard[ToolCapableProvider]:
    """The single spelling of the capability gate: the provider implements the
    tool-transport seam AND reports ``supports_tools``. On True, narrows the
    provider to ``ToolCapableProvider`` for the caller."""
    return isinstance(provider, ToolCapableProvider) and bool(provider.supports_tools)
