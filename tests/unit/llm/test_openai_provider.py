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
    from dungeon_daddy.llm.openai_provider import OpenAIProvider, DEFAULT_OPENAI_MODEL
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
