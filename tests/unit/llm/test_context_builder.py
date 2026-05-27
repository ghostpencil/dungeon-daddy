"""Tests for ContextBuilder — assembles compacted context docs into a system prompt."""
from __future__ import annotations

from dungeon_daddy.data.models import ContextDocType, Dungeon, DungeonMeta, Level
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.context_compactor import ContextCompactor


def _make_meta(**kwargs):
    defaults = dict(
        title="Iron Crypts",
        theme="Undead fortress",
        setting="A crumbling fortress beneath a dead volcano.",
        party="A band of mercenaries.",
        quest="Recover the Sunstone.",
        party_size=4,
        party_level=5,
        num_levels=2,
        complexity="Moderate",
    )
    defaults.update(kwargs)
    return DungeonMeta(**defaults)


def _make_level(**kwargs):
    defaults = dict(
        id=1, name="Antechamber", summary="Entry hall.", ecology="Undead patrol.",
        loop="lock_key", loops=[], width=10, height=10, entries=[], rooms=[], connections=[],
    )
    defaults.update(kwargs)
    return Level(**defaults)


def _make_dungeon(**kwargs):
    meta = kwargs.pop("meta", _make_meta())
    levels = kwargs.pop("levels", [_make_level()])
    return Dungeon(meta=meta, levels=levels)


def _compactor():
    """Real compactor with character-exact counter for deterministic tests."""
    return ContextCompactor(count_tokens=len)


# ---------------------------------------------------------------------------
# Tracer bullet: setting doc appears in the prompt
# ---------------------------------------------------------------------------

def test_setting_doc_appears_in_prompt(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    repo.save_context_doc("Iron Crypts", ContextDocType.SETTING, "The fortress lies beneath a volcano.")

    dungeon = _make_dungeon()
    builder = ContextBuilder(repo, _compactor())

    result = builder.build_system_prompt(dungeon)

    assert "fortress" in result


def test_party_doc_appears_in_prompt(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    repo.save_context_doc("Iron Crypts", ContextDocType.PARTY, "Four mercenaries seek the Sunstone.")

    dungeon = _make_dungeon()
    builder = ContextBuilder(repo, _compactor())

    result = builder.build_system_prompt(dungeon)

    assert "mercenaries" in result


def test_level_design_doc_included_when_level_id_given(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    repo.save_context_doc("Iron Crypts", ContextDocType.LEVEL_DESIGN, "Traps line the corridor.", level_id=1)

    dungeon = _make_dungeon()
    builder = ContextBuilder(repo, _compactor())

    result = builder.build_system_prompt(dungeon, level_id=1)

    assert "Traps" in result


def test_level_design_doc_absent_when_no_level_id(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    repo.save_context_doc("Iron Crypts", ContextDocType.LEVEL_DESIGN, "Traps line the corridor.", level_id=1)

    dungeon = _make_dungeon()
    builder = ContextBuilder(repo, _compactor())

    result = builder.build_system_prompt(dungeon)  # no level_id

    assert "Traps" not in result


def test_missing_docs_omitted_gracefully(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    # save only setting — party and level-design are missing
    repo.save_context_doc("Iron Crypts", ContextDocType.SETTING, "The fortress lies in ruins.")

    dungeon = _make_dungeon()
    builder = ContextBuilder(repo, _compactor())

    result = builder.build_system_prompt(dungeon, level_id=1)

    assert "fortress" in result
    assert result.strip() != ""
    # Only 1 of 3 possible docs was saved — result must be a single section with no separators
    sections = [s for s in result.split("\n\n") if s.strip()]
    assert len(sections) == 1


def test_builder_uses_save_name_when_set(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    # doc stored under the save_name slug, not the display title
    repo.save_context_doc("iron-crypts-slug", ContextDocType.SETTING, "Saved under slug.")

    dungeon = _make_dungeon(meta=_make_meta(save_name="iron-crypts-slug"))
    builder = ContextBuilder(repo, _compactor())

    result = builder.build_system_prompt(dungeon)

    assert "slug" in result


def test_long_doc_is_compacted_to_budget(tmp_path):
    from dungeon_daddy.llm.context_builder import ContextBuilder

    repo = DungeonRepository(tmp_path)
    long_text = "Word. " * 500  # 3000 chars >> budget
    repo.save_context_doc("Iron Crypts", ContextDocType.SETTING, long_text)

    dungeon = _make_dungeon()
    # character-exact counter, 50-char budget per doc
    compactor = ContextCompactor(count_tokens=len)
    builder = ContextBuilder(repo, compactor, max_tokens_per_doc=50)

    result = builder.build_system_prompt(dungeon)

    assert len(result) <= 50
