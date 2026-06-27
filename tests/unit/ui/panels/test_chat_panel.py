"""Pure-logic tests for ChatPanel bubble styling (Phase 51 Slice 9, §4.6).

The bubble fill/stroke/label is factored into the pure ``_bubble_style`` helper
so the role → treatment mapping is testable without an Arcade draw context.
"""
from dungeon_daddy.ui.panels.chat_panel import _bubble_style


def test_gm_role_is_labelled_gm():
    assert _bubble_style("gm").label == "GM"


def test_dungeon_voice_is_visually_distinct_from_dm_narration():
    # The Phase 51 dungeon-voice channel must not reuse the DM-narration bubble
    # (both previously rendered as the violet "◆ Dungeon" — Slice 8 carried gap b).
    dm = _bubble_style("dm")
    dungeon = _bubble_style("dungeon")
    assert dungeon.label != dm.label
    assert dungeon.fill != dm.fill  # darker/uncanny treatment


def test_unknown_role_falls_back_to_dm_treatment():
    assert _bubble_style("system").label == _bubble_style("dm").label
