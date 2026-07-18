"""The eval fixture must drive the production `ObservingProvider` stack, not a
bare provider. `ObservingProvider.complete_round` is exercised live only by the
narrator-lookup eval, so if the eval provider is left unwrapped that transport
goes untested end-to-end. These deterministic tests pin the wrapping seam
(`tests/evals/eval_provider.py`); they are unmarked, so they run in the default
suite without any live API call."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from dungeon_daddy.llm.provider import LLMMessage, LLMRoundResult, LLMToolDef
from dungeon_daddy.llm.telemetry import ObservingProvider
from tests.evals.eval_provider import observing_eval_provider


class _FakeToolProvider:
    """A minimal tool-capable provider (LLMProvider + ToolCapableProvider), the
    DI seam production wraps — no network, no SDK."""

    model_id = "fake-model"
    last_usage: tuple[int, int] | None = (7, 3)
    supports_tools = True

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> str:
        return "plain text"

    def stream(
        self, messages: list[LLMMessage], system: str = "", max_tokens: int = 1024
    ) -> Iterator[str]:
        yield "plain text"

    def complete_round(
        self,
        messages: list[LLMMessage],
        system: str = "",
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 1024,
    ) -> LLMRoundResult:
        return LLMRoundResult(text="round text")


def test_wraps_inner_in_observing_provider(tmp_path: Path) -> None:
    wrapped = observing_eval_provider(
        _FakeToolProvider(), agent="eval", log_path=tmp_path / "t.jsonl"
    )
    assert isinstance(wrapped, ObservingProvider)


def test_preserves_tool_transport_so_the_lookup_loop_still_fires(
    tmp_path: Path,
) -> None:
    # `dm_agent.respond` gates the lookup loop on `provider_supports_tools` then
    # drives `provider.complete_round`; the wrap must forward both or the
    # narrator-lookup eval would silently fall back to plain completion.
    wrapped = observing_eval_provider(
        _FakeToolProvider(), agent="eval", log_path=tmp_path / "t.jsonl"
    )
    assert wrapped.supports_tools is True
    result = wrapped.complete_round([LLMMessage(role="user", content="hi")])
    assert result.text == "round text"
