"""Tests for dungeon_daddy/llm/openai_provider.py"""
import pytest

# ---------------------------------------------------------------------------
# Behavior 1: model_id returns the configured model string
# ---------------------------------------------------------------------------

def test_openai_provider_model_id(mocker):
    mocker.patch("openai.OpenAI")
    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    p = OpenAIProvider(model="gpt-4o-mini", api_key="fake")
    assert p.model_id == "gpt-4o-mini"


def test_openai_provider_default_model(mocker):
    mocker.patch("openai.OpenAI")
    from dungeon_daddy.llm.openai_provider import DEFAULT_OPENAI_MODEL, OpenAIProvider
    p = OpenAIProvider(api_key="fake")
    assert p.model_id == DEFAULT_OPENAI_MODEL


def test_default_openai_model_is_nonempty_string():
    from dungeon_daddy.llm.openai_provider import DEFAULT_OPENAI_MODEL
    assert isinstance(DEFAULT_OPENAI_MODEL, str)
    assert len(DEFAULT_OPENAI_MODEL) > 0


# ---------------------------------------------------------------------------
# Behavior 2: complete() returns text from the API response
# ---------------------------------------------------------------------------

def test_openai_provider_complete_returns_text(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="A dark corridor."))
    ]
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    result = p.complete([LLMMessage(role="user", content="describe room")])
    assert result == "A dark corridor."


# ---------------------------------------------------------------------------
# Behavior 3: complete() passes system prompt as first system message
# ---------------------------------------------------------------------------

def test_openai_provider_complete_passes_system_as_message(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="ok"))
    ]
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete([LLMMessage(role="user", content="hi")], system="You are a wizard.")

    _, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "You are a wizard."}


def test_openai_provider_complete_omits_system_message_when_empty(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="ok"))
    ]
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete([LLMMessage(role="user", content="hi")], system="")

    _, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs["messages"]
    assert all(m["role"] != "system" for m in messages)


# ---------------------------------------------------------------------------
# Behavior 4: complete() raises LLMError on API failure
# ---------------------------------------------------------------------------

def test_openai_provider_raises_llm_error_not_api_error(mocker):
    import openai as _openai
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.side_effect = _openai.RateLimitError(
        "rate limit", response=mocker.MagicMock(), body={}
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMError, LLMMessage

    p = OpenAIProvider(api_key="fake")
    with pytest.raises(LLMError):
        p.complete([LLMMessage(role="user", content="hi")])


def test_openai_provider_does_not_leak_api_error(mocker):
    import openai as _openai
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.side_effect = _openai.APIConnectionError(
        request=mocker.MagicMock()
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    with pytest.raises(Exception) as exc_info:
        p.complete([LLMMessage(role="user", content="hi")])
    assert not isinstance(exc_info.value, _openai.APIError), (
        "OpenAIProvider must not leak openai.APIError to callers"
    )


# ---------------------------------------------------------------------------
# Behavior 5: stream() yields text chunks
# ---------------------------------------------------------------------------

def test_openai_provider_stream_yields_chunks(mocker):
    def _fake_chunks():
        for text in ["Hello", ", ", "world"]:
            chunk = mocker.MagicMock()
            chunk.choices = [mocker.MagicMock()]
            chunk.choices[0].delta.content = text
            yield chunk

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _fake_chunks()
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    chunks = list(p.stream([LLMMessage(role="user", content="hi")]))
    assert "".join(chunks) == "Hello, world"


def test_openai_provider_stream_skips_none_deltas(mocker):
    def _fake_chunks():
        for text in ["Hi", None, "!"]:
            chunk = mocker.MagicMock()
            chunk.choices = [mocker.MagicMock()]
            chunk.choices[0].delta.content = text
            yield chunk

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _fake_chunks()
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    chunks = list(p.stream([LLMMessage(role="user", content="hi")]))
    assert "".join(chunks) == "Hi!"


# ---------------------------------------------------------------------------
# Behavior 6: complete() forwards response_format to the API when provided
# ---------------------------------------------------------------------------

def test_openai_provider_complete_passes_response_format(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="{}"))
    ]
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete(
        [LLMMessage(role="user", content="hi")],
        response_format={"type": "json_object"},
    )

    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["response_format"] == {"type": "json_object"}


def test_openai_provider_complete_omits_response_format_when_none(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="ok"))
    ]
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete([LLMMessage(role="user", content="hi")])

    _, kwargs = mock_client.chat.completions.create.call_args
    assert "response_format" not in kwargs


# ---------------------------------------------------------------------------
# Slice B2 — complete_round tool-use transport
# ---------------------------------------------------------------------------

def _round_response(mocker, *, content=None, tool_calls=None, usage=None):
    """Build a fake chat.completions response for complete_round."""
    message = mocker.MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    response = mocker.MagicMock()
    response.choices = [mocker.MagicMock(message=message)]
    response.usage = usage
    return response


def test_openai_provider_supports_tools_is_true(mocker):
    mocker.patch("openai.OpenAI")
    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    p = OpenAIProvider(api_key="fake")
    assert p.supports_tools is True


def test_complete_round_returns_text_when_no_tool_calls(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(
        mocker, content="The door is ajar."
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    result = p.complete_round([LLMMessage(role="user", content="look")])
    assert result.text == "The door is ajar."
    assert result.tool_calls == []


def test_complete_round_translates_tool_defs_to_openai_format(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(mocker, content="ok")
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage, LLMToolDef

    schema = {"type": "object", "properties": {"query": {"type": "string"}}}
    tool = LLMToolDef(name="lookup_world", description="Search.", parameters=schema)

    p = OpenAIProvider(api_key="fake")
    p.complete_round([LLMMessage(role="user", content="hi")], tools=[tool])

    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["tools"] == [{
        "type": "function",
        "function": {
            "name": "lookup_world",
            "description": "Search.",
            "parameters": schema,
        },
    }]


def test_complete_round_omits_tools_when_none(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(mocker, content="ok")
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete_round([LLMMessage(role="user", content="hi")])

    _, kwargs = mock_client.chat.completions.create.call_args
    assert "tools" not in kwargs


def test_complete_round_parses_tool_calls_from_response(mocker):
    tc = mocker.MagicMock()
    tc.id = "call_abc"
    tc.function.name = "lookup_world"
    tc.function.arguments = '{"query": "mira", "limit": 5}'

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(
        mocker, content=None, tool_calls=[tc]
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    result = p.complete_round([LLMMessage(role="user", content="who is mira?")])

    assert result.text is None
    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert call.call_id == "call_abc"
    assert call.name == "lookup_world"
    assert call.arguments == {"query": "mira", "limit": 5}


def test_complete_round_forwards_tool_result_and_assistant_tool_calls(mocker):
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(mocker, content="done")
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage, LLMToolCall

    call = LLMToolCall(call_id="c1", name="lookup_world", arguments={"query": "x"})
    history = [
        LLMMessage(role="user", content="who is x?"),
        LLMMessage(role="assistant", content="", tool_calls=[call]),
        LLMMessage(role="tool", content="x is an NPC", tool_call_id="c1"),
    ]

    p = OpenAIProvider(api_key="fake")
    p.complete_round(history)

    _, kwargs = mock_client.chat.completions.create.call_args
    sent = kwargs["messages"]
    assistant = next(m for m in sent if m["role"] == "assistant")
    assert assistant["tool_calls"] == [{
        "id": "c1",
        "type": "function",
        "function": {"name": "lookup_world", "arguments": '{"query": "x"}'},
    }]
    tool_msg = next(m for m in sent if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "c1"
    assert tool_msg["content"] == "x is an NPC"


def test_complete_round_updates_last_usage(mocker):
    usage = mocker.MagicMock(prompt_tokens=11, completion_tokens=7)
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(
        mocker, content="ok", usage=usage
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete_round([LLMMessage(role="user", content="hi")])
    assert p.last_usage == (11, 7)


def test_complete_round_raises_llm_error_not_api_error(mocker):
    import openai as _openai
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.side_effect = _openai.RateLimitError(
        "rate limit", response=mocker.MagicMock(), body={}
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMError, LLMMessage

    p = OpenAIProvider(api_key="fake")
    with pytest.raises(LLMError):
        p.complete_round([LLMMessage(role="user", content="hi")])


def test_complete_round_raises_llm_error_on_malformed_tool_arguments(mocker):
    # A tool call truncated by max_tokens leaves invalid JSON in `arguments`.
    tc = mocker.MagicMock()
    tc.id = "call_x"
    tc.function.name = "lookup_world"
    tc.function.arguments = '{"query": "mir'  # truncated, not valid JSON

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _round_response(
        mocker, content=None, tool_calls=[tc]
    )
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMError, LLMMessage

    p = OpenAIProvider(api_key="fake")
    with pytest.raises(LLMError, match="malformed tool-call arguments"):
        p.complete_round([LLMMessage(role="user", content="hi")])
