"""Tests for dungeon_daddy/llm/provider.py and anthropic_provider.py"""
import pytest


# ---------------------------------------------------------------------------
# Shared mock provider used across this file
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, response="hello"):
        self._response = response
        self.calls = []

    def complete(self, messages, system="", max_tokens=1024):
        self.calls.append({"messages": messages, "system": system, "max_tokens": max_tokens})
        return self._response

    def stream(self, messages, system="", max_tokens=1024):
        for ch in self._response:
            yield ch

    @property
    def model_id(self):
        return "mock-model"


# ---------------------------------------------------------------------------
# Behavior 1: LLMMessage is a dataclass with role and content
# ---------------------------------------------------------------------------

def test_llm_message_has_role_and_content():
    from dungeon_daddy.llm.provider import LLMMessage
    msg = LLMMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"



# ---------------------------------------------------------------------------
# Behavior 2: LLMError is an Exception subclass
# ---------------------------------------------------------------------------

def test_llm_error_is_exception():
    from dungeon_daddy.llm.provider import LLMError
    assert issubclass(LLMError, Exception)


def test_llm_error_can_be_raised_and_caught():
    from dungeon_daddy.llm.provider import LLMError
    with pytest.raises(LLMError, match="something went wrong"):
        raise LLMError("something went wrong")


# ---------------------------------------------------------------------------
# Behavior 3: AnthropicProvider.model_id returns the model string
# ---------------------------------------------------------------------------

def test_anthropic_provider_model_id(mocker):
    mocker.patch("anthropic.Anthropic")
    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    p = AnthropicProvider(model="claude-test-model", api_key="fake")
    assert p.model_id == "claude-test-model"


def test_anthropic_provider_default_model(mocker):
    mocker.patch("anthropic.Anthropic")
    from dungeon_daddy.llm.anthropic_provider import (
        AnthropicProvider,
        DEFAULT_ANTHROPIC_MODEL,
    )
    p = AnthropicProvider(api_key="fake")
    assert p.model_id == DEFAULT_ANTHROPIC_MODEL


def test_default_anthropic_model_is_nonempty_string():
    from dungeon_daddy.llm.anthropic_provider import DEFAULT_ANTHROPIC_MODEL
    assert isinstance(DEFAULT_ANTHROPIC_MODEL, str)
    assert len(DEFAULT_ANTHROPIC_MODEL) > 0


# ---------------------------------------------------------------------------
# Behavior 4: AnthropicProvider.complete() returns text from the API
# ---------------------------------------------------------------------------

def test_anthropic_provider_complete_returns_text(mocker):
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value.content = [
        mocker.MagicMock(text="A dark corridor stretches ahead.")
    ]
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = AnthropicProvider(api_key="fake")
    result = p.complete([LLMMessage(role="user", content="describe room")])
    assert result == "A dark corridor stretches ahead."


def test_anthropic_provider_complete_passes_system_prompt(mocker):
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value.content = [mocker.MagicMock(text="ok")]
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = AnthropicProvider(api_key="fake")
    p.complete([LLMMessage(role="user", content="hi")], system="You are a wizard.")

    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["system"] == "You are a wizard."


# ---------------------------------------------------------------------------
# Behavior 5: AnthropicProvider.complete() raises LLMError on API failure
# ---------------------------------------------------------------------------

def test_anthropic_provider_raises_llm_error_not_api_error(mocker):
    import anthropic as _anthropic
    mock_client = mocker.MagicMock()
    mock_client.messages.create.side_effect = _anthropic.APIStatusError(
        "rate limit", response=mocker.MagicMock(), body={}
    )
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMError, LLMMessage

    p = AnthropicProvider(api_key="fake")
    with pytest.raises(LLMError):
        p.complete([LLMMessage(role="user", content="hi")])


def test_anthropic_provider_does_not_leak_api_error(mocker):
    import anthropic as _anthropic
    mock_client = mocker.MagicMock()
    mock_client.messages.create.side_effect = _anthropic.APIConnectionError(
        request=mocker.MagicMock()
    )
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMMessage
    import anthropic as _a

    p = AnthropicProvider(api_key="fake")
    with pytest.raises(Exception) as exc_info:
        p.complete([LLMMessage(role="user", content="hi")])
    assert not isinstance(exc_info.value, _a.APIError), (
        "AnthropicProvider must not leak anthropic.APIError to callers"
    )


# ---------------------------------------------------------------------------
# Behavior 6: AnthropicProvider.stream() yields text chunks
# ---------------------------------------------------------------------------

def test_anthropic_provider_stream_yields_chunks(mocker):
    mock_stream_ctx = mocker.MagicMock()
    mock_stream_ctx.__enter__ = mocker.MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = mocker.MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["Hello", ", ", "world"])

    mock_client = mocker.MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = AnthropicProvider(api_key="fake")
    chunks = list(p.stream([LLMMessage(role="user", content="hi")]))
    assert "".join(chunks) == "Hello, world"


# ---------------------------------------------------------------------------
# Behavior 7: LLMProvider Protocol — any object with complete/stream/model_id satisfies it
# ---------------------------------------------------------------------------

def test_mock_provider_satisfies_protocol():
    from dungeon_daddy.llm.provider import LLMProvider
    from typing import runtime_checkable, Protocol
    # We can't isinstance-check a non-runtime Protocol,
    # but we verify our mock has the required attributes.
    p = _MockProvider()
    assert callable(p.complete)
    assert callable(p.stream)
    assert isinstance(p.model_id, str)
