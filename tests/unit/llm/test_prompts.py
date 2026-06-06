"""Tests for dungeon_daddy/llm/prompts.py"""
import pytest

# ---------------------------------------------------------------------------
# Cycle 1: load_prompt happy path
# ---------------------------------------------------------------------------

def test_load_prompt_content_contains_expected_marker():
    from dungeon_daddy.llm.prompts import load_prompt
    text = load_prompt("dm_system")
    assert "Dungeon Master" in text


# ---------------------------------------------------------------------------
# Cycle 2: load_prompt missing file raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_load_prompt_missing_raises_file_not_found():
    from dungeon_daddy.llm.prompts import load_prompt
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_xyz")
