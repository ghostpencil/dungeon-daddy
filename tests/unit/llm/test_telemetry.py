"""Tests for dungeon_daddy/llm/telemetry.py"""
from __future__ import annotations

import json
import dataclasses

# ---------------------------------------------------------------------------
# Cycle 1: LLMCallRecord dataclass
# ---------------------------------------------------------------------------

def test_llm_call_record_fields():
    from dungeon_daddy.llm.telemetry import LLMCallRecord
    r = LLMCallRecord(
        agent="dm",
        model_id="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
        duration_ms=123.4,
        timestamp="2026-01-01T00:00:00",
    )
    assert r.agent == "dm"
    assert r.model_id == "gpt-4o"
    assert r.prompt_tokens == 100
    assert r.completion_tokens == 50
    assert r.duration_ms == 123.4
    assert r.timestamp == "2026-01-01T00:00:00"


def test_llm_call_record_serializes_to_json():
    from dungeon_daddy.llm.telemetry import LLMCallRecord
    r = LLMCallRecord(
        agent="wizard",
        model_id="gpt-4o-mini",
        prompt_tokens=200,
        completion_tokens=80,
        duration_ms=456.7,
        timestamp="2026-01-01T12:00:00",
    )
    data = json.loads(json.dumps(dataclasses.asdict(r)))
    assert data["agent"] == "wizard"
    assert data["prompt_tokens"] == 200
    assert data["completion_tokens"] == 80


# ---------------------------------------------------------------------------
# Cycle 2: TelemetryWriter
# ---------------------------------------------------------------------------

def test_telemetry_writer_creates_file_and_appends_json_line(tmp_path):
    from dungeon_daddy.llm.telemetry import LLMCallRecord, TelemetryWriter
    log_file = tmp_path / "llm_calls.jsonl"
    writer = TelemetryWriter(log_file)

    r = LLMCallRecord(
        agent="dm", model_id="gpt-4o",
        prompt_tokens=10, completion_tokens=5,
        duration_ms=100.0, timestamp="2026-01-01T00:00:00",
    )
    writer.record(r)

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["agent"] == "dm"
    assert data["prompt_tokens"] == 10


def test_telemetry_writer_appends_multiple_records(tmp_path):
    from dungeon_daddy.llm.telemetry import LLMCallRecord, TelemetryWriter
    log_file = tmp_path / "llm_calls.jsonl"
    writer = TelemetryWriter(log_file)

    for agent in ("dm", "wizard", "generator"):
        writer.record(LLMCallRecord(
            agent=agent, model_id="gpt-4o",
            prompt_tokens=1, completion_tokens=1,
            duration_ms=1.0, timestamp="2026-01-01T00:00:00",
        ))

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    agents = [json.loads(l)["agent"] for l in lines]
    assert agents == ["dm", "wizard", "generator"]


# ---------------------------------------------------------------------------
# Cycle 3-4: ObservingProvider
# ---------------------------------------------------------------------------

def _make_mock_provider(mocker, *, text="response text", last_usage=(10, 5)):
    p = mocker.MagicMock()
    p.complete.return_value = text
    p.model_id = "gpt-4o"
    p.last_usage = last_usage
    return p


def test_observing_provider_complete_returns_inner_result(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter
    from dungeon_daddy.llm.provider import LLMMessage

    inner = _make_mock_provider(mocker, text="A dark room.")
    writer = TelemetryWriter(tmp_path / "llm_calls.jsonl")
    op = ObservingProvider(inner, agent="dm", writer=writer)

    result = op.complete([LLMMessage(role="user", content="describe")], system="You are DM.")
    assert result == "A dark room."


def test_observing_provider_complete_delegates_args(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter
    from dungeon_daddy.llm.provider import LLMMessage

    inner = _make_mock_provider(mocker)
    writer = TelemetryWriter(tmp_path / "llm_calls.jsonl")
    op = ObservingProvider(inner, agent="dm", writer=writer)

    msgs = [LLMMessage(role="user", content="hi")]
    op.complete(msgs, system="sys", max_tokens=512)
    inner.complete.assert_called_once_with(msgs, system="sys", max_tokens=512, response_format=None)


def test_observing_provider_complete_writes_one_record(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter
    from dungeon_daddy.llm.provider import LLMMessage

    inner = _make_mock_provider(mocker, last_usage=(100, 40))
    log_file = tmp_path / "llm_calls.jsonl"
    writer = TelemetryWriter(log_file)
    op = ObservingProvider(inner, agent="wizard", writer=writer)

    op.complete([LLMMessage(role="user", content="hi")])

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["agent"] == "wizard"
    assert rec["model_id"] == "gpt-4o"
    assert rec["prompt_tokens"] == 100
    assert rec["completion_tokens"] == 40
    assert rec["duration_ms"] >= 0
    assert rec["timestamp"]  # non-empty ISO string


def test_observing_provider_model_id_delegates(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))
    assert op.model_id == "gpt-4o"


# ---------------------------------------------------------------------------
# Cycle 5: OpenAIProvider.last_usage
# ---------------------------------------------------------------------------

def test_openai_provider_last_usage_is_none_before_any_call(mocker):
    mocker.patch("openai.OpenAI")
    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    p = OpenAIProvider(api_key="fake")
    assert p.last_usage is None


def test_openai_provider_last_usage_returns_token_counts_after_complete(mocker):
    mock_client = mocker.MagicMock()
    usage = mocker.MagicMock()
    usage.prompt_tokens = 42
    usage.completion_tokens = 17
    mock_client.chat.completions.create.return_value.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="ok"))
    ]
    mock_client.chat.completions.create.return_value.usage = usage
    mocker.patch("openai.OpenAI", return_value=mock_client)

    from dungeon_daddy.llm.openai_provider import OpenAIProvider
    from dungeon_daddy.llm.provider import LLMMessage

    p = OpenAIProvider(api_key="fake")
    p.complete([LLMMessage(role="user", content="hi")])
    assert p.last_usage == (42, 17)


# ---------------------------------------------------------------------------
# Cycle 6: ObservingProvider.stream() records after all chunks yielded
# ---------------------------------------------------------------------------

def test_observing_provider_stream_yields_chunks(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter
    from dungeon_daddy.llm.provider import LLMMessage

    inner = _make_mock_provider(mocker)
    inner.stream.return_value = iter(["Hello", ", ", "world"])
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))

    chunks = list(op.stream([LLMMessage(role="user", content="hi")]))
    assert "".join(chunks) == "Hello, world"


def test_observing_provider_stream_writes_one_record(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter
    from dungeon_daddy.llm.provider import LLMMessage

    inner = _make_mock_provider(mocker, last_usage=(30, 15))
    inner.stream.return_value = iter(["chunk"])
    log_file = tmp_path / "llm_calls.jsonl"
    op = ObservingProvider(inner, agent="generator", writer=TelemetryWriter(log_file))

    list(op.stream([LLMMessage(role="user", content="hi")]))

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["agent"] == "generator"
    assert rec["prompt_tokens"] == 30
    assert rec["completion_tokens"] == 15


# ---------------------------------------------------------------------------
# Cycle 7: window.py factory wiring
# ---------------------------------------------------------------------------

def test_build_dm_agent_wraps_provider_with_observing_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    log_file = tmp_path / "llm_calls.jsonl"

    from unittest.mock import patch, MagicMock
    with patch("dungeon_daddy.llm.openai_provider.OpenAIProvider") as MockProvider, \
         patch("dungeon_daddy.llm.agents.dm_agent.DungeonMasterAgent") as MockAgent, \
         patch("dungeon_daddy.llm.telemetry.ObservingProvider") as MockObserving:
        MockObserving.return_value = MagicMock()
        from dungeon_daddy.window import _build_dm_agent
        _build_dm_agent(log_file)

    MockObserving.assert_called_once()
    _, kwargs = MockObserving.call_args
    assert kwargs["agent"] == "dm"


def test_build_agents_wraps_each_agent_with_observing_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    log_file = tmp_path / "llm_calls.jsonl"

    from unittest.mock import patch, MagicMock, call
    with patch("dungeon_daddy.llm.openai_provider.OpenAIProvider"), \
         patch("dungeon_daddy.llm.agents.wizard_agent.DungeonWizardAgent"), \
         patch("dungeon_daddy.llm.agents.generator_agent.DungeonGeneratorAgent"), \
         patch("dungeon_daddy.llm.agents.design_agent.DesignAgent"), \
         patch("dungeon_daddy.data.models.LoopPatternCatalog"), \
         patch("dungeon_daddy.llm.telemetry.ObservingProvider") as MockObserving:
        MockObserving.return_value = MagicMock()
        from dungeon_daddy.window import _build_agents
        _build_agents(log_file)

    agent_names = [call.kwargs["agent"] for call in MockObserving.call_args_list]
    assert set(agent_names) == {"wizard", "generator", "design"}
