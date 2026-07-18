"""Tests for dungeon_daddy/llm/telemetry.py"""
from __future__ import annotations

import dataclasses
import json

# ---------------------------------------------------------------------------
# Cycle 1: LLMCallRecord dataclass
# ---------------------------------------------------------------------------

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
    agents = [json.loads(line)["agent"] for line in lines]
    assert agents == ["dm", "wizard", "generator"]


# ---------------------------------------------------------------------------
# Cycle 3-4: ObservingProvider
# ---------------------------------------------------------------------------

def _make_mock_provider(mocker, *, text="response text", last_usage=(10, 5)):
    p = mocker.MagicMock()
    p.complete.return_value = text
    p.model_id = "gpt-4o"
    p.last_usage = last_usage
    # Attach the tool-transport members as *real* instance attributes rather
    # than lazily via MagicMock.__getattr__. Python 3.12's runtime_checkable
    # isinstance() uses inspect.getattr_static, which bypasses __getattr__, so a
    # bare mock fails isinstance(p, ToolCapableProvider) — both protocol attrs
    # (complete_round, supports_tools) must live in the instance dict where
    # getattr_static looks. Value of supports_tools is asserted where it matters.
    p.supports_tools = True
    p.complete_round = mocker.MagicMock()
    return p


def test_observing_provider_complete_returns_inner_result(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker, text="A dark room.")
    writer = TelemetryWriter(tmp_path / "llm_calls.jsonl")
    op = ObservingProvider(inner, agent="dm", writer=writer)

    result = op.complete([LLMMessage(role="user", content="describe")], system="You are DM.")
    assert result == "A dark room."


def test_observing_provider_complete_delegates_args(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    writer = TelemetryWriter(tmp_path / "llm_calls.jsonl")
    op = ObservingProvider(inner, agent="dm", writer=writer)

    msgs = [LLMMessage(role="user", content="hi")]
    op.complete(msgs, system="sys", max_tokens=512)
    inner.complete.assert_called_once_with(msgs, system="sys", max_tokens=512, response_format=None)


def test_observing_provider_complete_writes_one_record(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

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
# Slice B2: ObservingProvider forwards tool-use transport (complete_round)
# ---------------------------------------------------------------------------

def test_observing_provider_supports_tools_reflects_inner(mocker, tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    inner.supports_tools = True
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))
    assert op.supports_tools is True


def test_observing_provider_supports_tools_false_when_inner_lacks_it(tmp_path):
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    class _NoTools:
        model_id = "x"
        last_usage = None

    op = ObservingProvider(_NoTools(), agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))
    assert op.supports_tools is False


def test_observing_provider_complete_round_delegates_and_returns_result(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage, LLMRoundResult, LLMToolDef
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    expected = LLMRoundResult(text="ok")
    inner.complete_round.return_value = expected
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))

    msgs = [LLMMessage(role="user", content="hi")]
    tools = [LLMToolDef(name="lookup_world", description="d", parameters={})]
    result = op.complete_round(msgs, system="sys", tools=tools, max_tokens=256)

    assert result is expected
    inner.complete_round.assert_called_once_with(msgs, system="sys", tools=tools, max_tokens=256)


def test_observing_provider_complete_round_writes_one_record(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage, LLMRoundResult
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker, last_usage=(100, 40))
    inner.complete_round.return_value = LLMRoundResult(text="ok")
    log_file = tmp_path / "llm_calls.jsonl"
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(log_file))

    op.complete_round([LLMMessage(role="user", content="hi")])

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["agent"] == "dm"
    assert rec["prompt_tokens"] == 100
    assert rec["completion_tokens"] == 40


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
    from dungeon_daddy.llm.provider import LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    inner.stream.return_value = iter(["Hello", ", ", "world"])
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))

    chunks = list(op.stream([LLMMessage(role="user", content="hi")]))
    assert "".join(chunks) == "Hello, world"


def test_observing_provider_stream_writes_one_record(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

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
# Cycle 7 (IP-7): prompt_name and prompt_hash in LLMCallRecord
# ---------------------------------------------------------------------------

def test_llm_call_record_prompt_fields_roundtrip_json():
    from dungeon_daddy.llm.telemetry import LLMCallRecord
    r = LLMCallRecord(
        agent="dm", model_id="gpt-4o",
        prompt_tokens=1, completion_tokens=1,
        duration_ms=1.0, timestamp="2026-01-01T00:00:00",
        prompt_name="dm_system", prompt_hash="abc12345",
    )
    data = json.loads(json.dumps(dataclasses.asdict(r)))
    assert data["prompt_name"] == "dm_system"
    assert data["prompt_hash"] == "abc12345"


def test_observing_provider_record_includes_prompt_info(mocker, tmp_path):
    from dungeon_daddy.llm.provider import LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker, last_usage=(5, 3))
    log_file = tmp_path / "llm_calls.jsonl"
    op = ObservingProvider(
        inner, agent="dm", writer=TelemetryWriter(log_file),
        prompt_name="dm_system", prompt_hash="abc12345",
    )
    op.complete([LLMMessage(role="user", content="hi")])

    rec = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert rec["prompt_name"] == "dm_system"
    assert rec["prompt_hash"] == "abc12345"


# ---------------------------------------------------------------------------
# Cycle 9: window.py factory wiring
# ---------------------------------------------------------------------------

def test_build_dm_agent_wraps_provider_with_observing_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    log_file = tmp_path / "llm_calls.jsonl"

    from unittest.mock import MagicMock, patch
    with patch("dungeon_daddy.llm.openai_provider.OpenAIProvider"), \
         patch("dungeon_daddy.llm.agents.dm_agent.DungeonMasterAgent"), \
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

    from unittest.mock import MagicMock, patch
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


# ---------------------------------------------------------------------------
# Cleanup item 2: tool capability is isinstance-detected (ToolCapableProvider)
# ---------------------------------------------------------------------------

def test_observing_provider_complete_round_on_toolless_inner_raises_llm_error(tmp_path):
    # Callers gate on supports_tools; if one slips through anyway it must get
    # the provider-contract exception, not an AttributeError.
    import pytest

    from dungeon_daddy.llm.provider import LLMError, LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    class _NoTools:
        model_id = "x"
        last_usage = None

    op = ObservingProvider(_NoTools(), agent="dm", writer=TelemetryWriter(tmp_path / "f.jsonl"))
    with pytest.raises(LLMError, match="tool"):
        op.complete_round([LLMMessage(role="user", content="hi")])


# ---------------------------------------------------------------------------
# Cleanup item 5: a failed call still writes its telemetry record — failing
# turns must not be invisible in the data used to spot them.
# ---------------------------------------------------------------------------

def test_observing_provider_complete_round_records_a_failed_call(mocker, tmp_path):
    import pytest

    from dungeon_daddy.llm.provider import LLMError, LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    inner.complete_round.side_effect = LLMError("rate limited")
    log_file = tmp_path / "llm_calls.jsonl"
    op = ObservingProvider(inner, agent="dm", writer=TelemetryWriter(log_file))

    with pytest.raises(LLMError, match="rate limited"):
        op.complete_round([LLMMessage(role="user", content="hi")])

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["agent"] == "dm"
    # The inner provider's last_usage is stale on failure (it only updates on
    # success) — the mock still reports (10, 5). Recording those would
    # double-count the previous call's tokens in the cost report.
    assert rec["prompt_tokens"] == 0
    assert rec["completion_tokens"] == 0


def test_observing_provider_complete_records_a_failed_call(mocker, tmp_path):
    import pytest

    from dungeon_daddy.llm.provider import LLMError, LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    inner.complete.side_effect = LLMError("rate limited")
    log_file = tmp_path / "llm_calls.jsonl"
    op = ObservingProvider(inner, agent="wizard", writer=TelemetryWriter(log_file))

    with pytest.raises(LLMError, match="rate limited"):
        op.complete([LLMMessage(role="user", content="hi")])

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["agent"] == "wizard"
    assert rec["prompt_tokens"] == 0  # stale last_usage must not be recorded
    assert rec["completion_tokens"] == 0


def test_telemetry_write_failure_does_not_mask_the_provider_error(mocker, tmp_path, caplog):
    # An OSError raised while recording the failure must not replace the
    # in-flight LLMError — callers would see a telemetry I/O message instead
    # of the real cause (e.g. a rate limit).
    import logging

    import pytest

    from dungeon_daddy.llm.provider import LLMError, LLMMessage
    from dungeon_daddy.llm.telemetry import ObservingProvider, TelemetryWriter

    inner = _make_mock_provider(mocker)
    inner.complete.side_effect = LLMError("rate limited")
    writer = TelemetryWriter(tmp_path / "f.jsonl")
    mocker.patch.object(writer, "record", side_effect=OSError("disk full"))
    op = ObservingProvider(inner, agent="dm", writer=writer)

    with caplog.at_level(logging.ERROR, logger="dungeon_daddy.llm.telemetry"):
        with pytest.raises(LLMError, match="rate limited"):
            op.complete([LLMMessage(role="user", content="hi")])

    # The swallow must stay observable: a bare `except: pass` would keep the
    # LLMError propagating (asserted above) while silently dropping the failure
    # log — the exact signal item 5 exists to preserve. Pin the log too.
    assert any(
        "telemetry write failed" in record.getMessage() for record in caplog.records
    )
