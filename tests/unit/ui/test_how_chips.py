from __future__ import annotations


def _build(**kw):
    from dungeon_daddy.ui.how_chips import build_how_chips
    return build_how_chips(**kw)


# ---------------------------------------------------------------------------
# Base chips — always offered for an ordinary exit
# ---------------------------------------------------------------------------

def test_base_chips_for_plain_exit():
    chips = _build()
    keys = [c.how for c in chips]
    assert keys == ["cautiously", "quickly", "boldly"]


# ---------------------------------------------------------------------------
# stealthily — only when an actor has sense >= 1
# ---------------------------------------------------------------------------

def test_stealthily_hidden_without_sense():
    keys = [c.how for c in _build(max_sense=0)]
    assert "stealthily" not in keys


def test_stealthily_offered_with_sense():
    keys = [c.how for c in _build(max_sense=1)]
    assert "stealthily" in keys


# ---------------------------------------------------------------------------
# Contextual chips — surfaced only when the room/exit warrants them
# ---------------------------------------------------------------------------

def test_deliberately_for_one_way_exit():
    keys = [c.how for c in _build(one_way=True)]
    assert "deliberately" in keys


def test_deliberately_absent_without_one_way():
    keys = [c.how for c in _build()]
    assert "deliberately" not in keys


def test_reverently_for_ritual_connector():
    keys = [c.how for c in _build(ritual_connector=True)]
    assert "reverently" in keys


def test_recklessly_for_armed_trap_clock():
    keys = [c.how for c in _build(armed_trap_clock=True)]
    assert "recklessly" in keys
