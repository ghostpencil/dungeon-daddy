"""Integration tests — generate_all_context_docs → save → load → compact → system prompt."""
from __future__ import annotations

import pytest

from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.context_builder import ContextBuilder
from dungeon_daddy.llm.context_compactor import ContextCompactor
from dungeon_daddy.llm.context_docs import generate_all_context_docs


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_meta() -> DungeonMeta:
    return DungeonMeta(
        title="The Iron Crypts",
        theme="Undead fortress",
        setting="A crumbling fortress beneath a dead volcano.",
        party="A band of mercenaries hired to retrieve a stolen relic.",
        quest="Recover the Sunstone from the lich Malachar.",
        party_size=4,
        party_level=5,
        save_name="iron_crypts",
    )


def _make_level(level_id: int = 1, name: str = "The Antechamber") -> Level:
    return Level(
        id=level_id, name=name, summary="A wide entry hall with crumbling pillars.",
        ecology="Undead guards patrol in shifts.", loop="lock_key", loops=[],
        width=10, height=5, entries=[], rooms=[], connections=[],
    )


def _setup(tmp_path, levels=None):
    repo = DungeonRepository(tmp_path)
    dungeon = Dungeon(meta=_make_meta(), levels=levels or [_make_level()])
    generate_all_context_docs(dungeon, "iron_crypts", repo)
    builder = ContextBuilder(repo, ContextCompactor())
    return dungeon, builder


# ---------------------------------------------------------------------------
# Behavior 1: setting doc content appears in prompt (tracer bullet)
# ---------------------------------------------------------------------------

def test_setting_section_appears_in_system_prompt(tmp_path):
    dungeon, builder = _setup(tmp_path)
    prompt = builder.build_system_prompt(dungeon)
    assert "The Iron Crypts" in prompt


# ---------------------------------------------------------------------------
# Behavior 2: party doc content appears in prompt
# ---------------------------------------------------------------------------

def test_party_section_appears_in_system_prompt(tmp_path):
    dungeon, builder = _setup(tmp_path)
    prompt = builder.build_system_prompt(dungeon)
    assert "mercenaries" in prompt


# ---------------------------------------------------------------------------
# Behavior 3: level design content appears when level_id is passed
# ---------------------------------------------------------------------------

def test_level_design_section_appears_in_system_prompt(tmp_path):
    dungeon, builder = _setup(tmp_path)
    prompt = builder.build_system_prompt(dungeon, level_id=1)
    assert "The Antechamber" in prompt
