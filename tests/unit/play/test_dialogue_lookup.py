"""Slice B4d — DialogueCoordinator wires the `lookup_world` executor (spec §10).

The dungeon-voice worker hands the ``DungeonVoiceAgent`` a read-only
``LookupService`` executor scoped to the active campaign, with the L7 overlap
set seeded from the recent memories already in the voice context. ``None`` when
no campaign is attached.
"""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.llm.provider import LLMToolCall
from dungeon_daddy.play.narration import DMResult
from tests.unit.play.test_dialogue import _make


class _StubVoiceAgent:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def respond(self, **kwargs) -> str:  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        return "I remember her."


def test_send_dungeon_line_passes_working_lookup_executor(tmp_path: Path) -> None:
    agent = _StubVoiceAgent()
    coord, _chat, repo, _session, narr = _make(tmp_path, voice_agent=agent)
    repo.save_actor("npc-mira", "camp-1", "npc", "mira", "Mira", tags=["actor:npc:mira"])

    coord.begin_dialogue(kind="dungeon", room_id="r1")
    coord.send_dungeon_line("tell me about mira")

    assert narr.worker is not None
    result = narr.worker()
    assert isinstance(result, DMResult)

    lookup = agent.calls[0]["lookup"]
    assert callable(lookup)
    payload = json.loads(lookup(LLMToolCall("c1", "lookup_world", {"query": "mira"})))
    assert payload["results"][0]["id"] == "npc-mira"


def test_lookup_is_none_without_active_campaign(tmp_path: Path) -> None:
    # Cleanup item 11.1: drive the public ``send_dungeon_line`` seam (as the
    # narration-side twin ``test_narration_lookup`` does), not the private
    # ``_build_lookup_executor``. With no active campaign the agent must be
    # handed ``lookup=None`` (it falls back to ``complete``).
    agent = _StubVoiceAgent()
    coord, _chat, _repo, session, narr = _make(tmp_path, voice_agent=agent)
    session.campaign_id = None  # no active campaign → no lookup seam

    coord.begin_dialogue(kind="dungeon", room_id="r1")
    coord.send_dungeon_line("tell me about mira")

    assert narr.worker is not None
    result = narr.worker()
    assert isinstance(result, DMResult)
    assert agent.calls[0]["lookup"] is None


# -- Slice B4e — voice-path lookups ride back on the DMResult ----------------


class _LookupCallingVoiceAgent:
    """A voice agent whose respond() invokes the injected lookup executor once."""

    def respond(self, **kwargs) -> str:  # type: ignore[no-untyped-def]
        lookup = kwargs.get("lookup")
        if lookup is not None:
            lookup(LLMToolCall("c1", "lookup_world", {"query": "mira"}))
        return "I remember her."


def test_send_dungeon_line_attaches_lookups_to_result(tmp_path: Path) -> None:
    agent = _LookupCallingVoiceAgent()
    coord, _chat, repo, _session, narr = _make(tmp_path, voice_agent=agent)
    repo.save_actor("npc-mira", "camp-1", "npc", "mira", "Mira", tags=["actor:npc:mira"])

    coord.begin_dialogue(kind="dungeon", room_id="r1")
    coord.send_dungeon_line("tell me about mira")

    assert narr.worker is not None
    result = narr.worker()
    assert len(result.lookups) == 1
    assert result.lookups[0].query == "mira"
