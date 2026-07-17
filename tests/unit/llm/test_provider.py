"""Tests for dungeon_daddy/llm/provider.py and anthropic_provider.py"""
import pytest

# ---------------------------------------------------------------------------
# Behavior 2: LLMError is an Exception subclass
# ---------------------------------------------------------------------------

def test_llm_error_can_be_raised_and_caught():
    from dungeon_daddy.llm.provider import LLMError
    with pytest.raises(LLMError, match="something went wrong"):
        raise LLMError("something went wrong")


# ---------------------------------------------------------------------------
# Slice B2 — provider-neutral tool-use types
# ---------------------------------------------------------------------------

def test_llm_tool_def_holds_name_description_parameters():
    from dungeon_daddy.llm.provider import LLMToolDef
    schema = {"type": "object", "properties": {"query": {"type": "string"}}}
    tool = LLMToolDef(name="lookup_world", description="Search the world.", parameters=schema)
    assert tool.name == "lookup_world"
    assert tool.description == "Search the world."
    assert tool.parameters == schema


def test_llm_tool_call_holds_call_id_name_arguments():
    from dungeon_daddy.llm.provider import LLMToolCall
    call = LLMToolCall(call_id="call_1", name="lookup_world", arguments={"query": "mira"})
    assert call.call_id == "call_1"
    assert call.name == "lookup_world"
    assert call.arguments == {"query": "mira"}


def test_llm_round_result_defaults_to_no_text_and_empty_tool_calls():
    from dungeon_daddy.llm.provider import LLMRoundResult
    result = LLMRoundResult()
    assert result.text is None
    assert result.tool_calls == []


def test_llm_round_result_carries_text_and_tool_calls():
    from dungeon_daddy.llm.provider import LLMRoundResult, LLMToolCall
    call = LLMToolCall(call_id="c1", name="lookup_world", arguments={})
    result = LLMRoundResult(text="hi", tool_calls=[call])
    assert result.text == "hi"
    assert result.tool_calls == [call]


def test_llm_message_stays_back_compatible_with_role_and_content_only():
    from dungeon_daddy.llm.provider import LLMMessage
    msg = LLMMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.tool_call_id is None
    assert msg.tool_calls is None


def test_llm_message_can_carry_tool_result_and_assistant_tool_calls():
    from dungeon_daddy.llm.provider import LLMMessage, LLMToolCall
    call = LLMToolCall(call_id="c1", name="lookup_world", arguments={"query": "x"})
    assistant = LLMMessage(role="assistant", content="", tool_calls=[call])
    tool_result = LLMMessage(role="tool", content="rows...", tool_call_id="c1")
    assert assistant.tool_calls == [call]
    assert tool_result.role == "tool"
    assert tool_result.tool_call_id == "c1"


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
        DEFAULT_ANTHROPIC_MODEL,
        AnthropicProvider,
    )
    p = AnthropicProvider(api_key="fake")
    assert p.model_id == DEFAULT_ANTHROPIC_MODEL


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

    import anthropic as _a

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMMessage

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
# Behavior 8: AnthropicProvider.complete() accepts response_format and ignores it
# ---------------------------------------------------------------------------

def test_anthropic_provider_accepts_response_format_without_error(mocker):
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value.content = [mocker.MagicMock(text="ok")]
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    from dungeon_daddy.llm.anthropic_provider import AnthropicProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = AnthropicProvider(api_key="fake")
    result = p.complete(
        [LLMMessage(role="user", content="hi")],
        response_format={"type": "json_object"},
    )
    assert result == "ok"
    _, kwargs = mock_client.messages.create.call_args
    assert "response_format" not in kwargs
