"""Tests for ContextDocGenerator — derives context docs from Dungeon data."""
import pytest


def _make_meta(**kwargs):
    from dungeon_daddy.data.models import DungeonMeta
    defaults = dict(
        title="The Iron Crypts",
        theme="Undead fortress",
        setting="A crumbling fortress beneath a dead volcano.",
        party="A band of mercenaries hired to retrieve a stolen relic.",
        quest="Recover the Sunstone from the lich Malachar.",
        party_size=4,
        party_level=5,
        num_levels=3,
        complexity="Moderate",
    )
    defaults.update(kwargs)
    return DungeonMeta(**defaults)


def _make_level(**kwargs):
    from dungeon_daddy.data.models import Level
    defaults = dict(
        id=1,
        name="The Antechamber",
        summary="A wide entry hall with crumbling pillars.",
        ecology="Undead guards patrol in shifts.",
        loop="lock_key",
        loops=[],
        width=10,
        height=10,
        entries=[],
        rooms=[],
        connections=[],
    )
    defaults.update(kwargs)
    return Level(**defaults)


# ---------------------------------------------------------------------------
# generate_setting_doc
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expected", [
    "The Iron Crypts",
    "Undead fortress",
    "crumbling fortress",
    "Sunstone",
])
def test_setting_doc_contains(expected):
    from dungeon_daddy.llm.context_docs import generate_setting_doc
    doc = generate_setting_doc(_make_meta())
    assert expected in doc


# ---------------------------------------------------------------------------
# generate_party_doc
# ---------------------------------------------------------------------------

def test_party_doc_contains_party_narrative():
    from dungeon_daddy.llm.context_docs import generate_party_doc
    meta = _make_meta()
    doc = generate_party_doc(meta)
    assert "mercenaries" in doc


def test_party_doc_contains_party_size():
    from dungeon_daddy.llm.context_docs import generate_party_doc
    meta = _make_meta()
    doc = generate_party_doc(meta)
    assert "4" in doc


def test_party_doc_contains_party_level():
    from dungeon_daddy.llm.context_docs import generate_party_doc
    meta = _make_meta()
    doc = generate_party_doc(meta)
    assert "5" in doc


# ---------------------------------------------------------------------------
# generate_level_design_doc
# ---------------------------------------------------------------------------

def test_level_design_doc_contains_level_name():
    from dungeon_daddy.llm.context_docs import generate_level_design_doc
    level = _make_level()
    doc = generate_level_design_doc(level)
    assert "The Antechamber" in doc


def test_level_design_doc_contains_ecology():
    from dungeon_daddy.llm.context_docs import generate_level_design_doc
    level = _make_level()
    doc = generate_level_design_doc(level)
    assert "Undead guards patrol" in doc


def test_level_design_doc_contains_summary():
    from dungeon_daddy.llm.context_docs import generate_level_design_doc
    level = _make_level()
    doc = generate_level_design_doc(level)
    assert "crumbling pillars" in doc


# ---------------------------------------------------------------------------
# generate_all_context_docs
# ---------------------------------------------------------------------------

def test_generate_all_saves_setting_and_party(tmp_path):
    from dungeon_daddy.data.models import ContextDocType, Dungeon
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.llm.context_docs import generate_all_context_docs

    repo = DungeonRepository(tmp_path)
    meta = _make_meta()
    dungeon = Dungeon(meta=meta, levels=[_make_level(id=1), _make_level(id=2, name="Lower Hall")])

    generate_all_context_docs(dungeon, "iron_crypts", repo)

    assert repo.load_context_doc("iron_crypts", ContextDocType.SETTING) != ""
    assert repo.load_context_doc("iron_crypts", ContextDocType.PARTY) != ""


def test_generate_all_saves_one_level_doc_per_level(tmp_path):
    from dungeon_daddy.data.models import ContextDocType, Dungeon
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.llm.context_docs import generate_all_context_docs

    repo = DungeonRepository(tmp_path)
    meta = _make_meta()
    dungeon = Dungeon(meta=meta, levels=[_make_level(id=1), _make_level(id=2, name="Lower Hall")])

    generate_all_context_docs(dungeon, "iron_crypts", repo)

    assert repo.load_context_doc("iron_crypts", ContextDocType.LEVEL_DESIGN, level_id=1) != ""
    assert repo.load_context_doc("iron_crypts", ContextDocType.LEVEL_DESIGN, level_id=2) != ""


def test_generate_all_skips_existing_by_default(tmp_path):
    from dungeon_daddy.data.models import ContextDocType, Dungeon
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.llm.context_docs import generate_all_context_docs

    repo = DungeonRepository(tmp_path)
    meta = _make_meta()
    dungeon = Dungeon(meta=meta, levels=[_make_level(id=1)])

    repo.save_context_doc("iron_crypts", ContextDocType.SETTING, "custom content")
    generate_all_context_docs(dungeon, "iron_crypts", repo)

    assert repo.load_context_doc("iron_crypts", ContextDocType.SETTING) == "custom content"


def test_generate_all_overwrites_when_skip_existing_false(tmp_path):
    from dungeon_daddy.data.models import ContextDocType, Dungeon
    from dungeon_daddy.data.repository import DungeonRepository
    from dungeon_daddy.llm.context_docs import generate_all_context_docs

    repo = DungeonRepository(tmp_path)
    meta = _make_meta()
    dungeon = Dungeon(meta=meta, levels=[_make_level(id=1)])

    repo.save_context_doc("iron_crypts", ContextDocType.SETTING, "custom content")
    generate_all_context_docs(dungeon, "iron_crypts", repo, skip_existing=False)

    result = repo.load_context_doc("iron_crypts", ContextDocType.SETTING)
    assert result != "custom content"
    assert "The Iron Crypts" in result
