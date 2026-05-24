"""Tests for DungeonDaddyWindow — unit-level, no arcade initialisation."""
from unittest.mock import MagicMock, patch

from dungeon_daddy.data.models import Dungeon, DungeonMeta, ValidationResult


def _make_dungeon(save_name=None) -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(
            title="Iron Crypts", theme="Undead", setting="S", party="P", quest="Q",
            save_name=save_name,
        ),
        levels=[],
    )


def _make_window(dungeon: Dungeon):
    """Construct DungeonDaddyWindow bypassing arcade.__init__."""
    from dungeon_daddy.window import DungeonDaddyWindow
    win = DungeonDaddyWindow.__new__(DungeonDaddyWindow)
    win._repo = MagicMock()
    win._play_view = MagicMock()
    win._play_view._dungeon = None
    win._play_view._state = None
    win._design_view = MagicMock()
    win._design_view._dungeon = dungeon
    return win


# ---------------------------------------------------------------------------
# save_dungeon — CD-3
# ---------------------------------------------------------------------------

def test_save_dungeon_uses_title_when_no_save_name():
    win = _make_window(_make_dungeon())
    with patch("dungeon_daddy.llm.context_docs.generate_all_context_docs"):
        win.save_dungeon()
    win._repo.save.assert_called_once_with(win._design_view._dungeon, "Iron Crypts")


def test_save_dungeon_uses_save_name_when_set():
    win = _make_window(_make_dungeon(save_name="iron-crypts"))
    with patch("dungeon_daddy.llm.context_docs.generate_all_context_docs"):
        win.save_dungeon()
    win._repo.save.assert_called_once_with(win._design_view._dungeon, "iron-crypts")


# ---------------------------------------------------------------------------
# open_dungeon
# ---------------------------------------------------------------------------

def test_open_dungeon_loads_dungeon_when_name_returned():
    dungeon = _make_dungeon()
    win = _make_window(dungeon)
    win._repo.load.return_value = dungeon
    win.switch_mode = MagicMock()

    win.open_dungeon(_pick_fn=lambda: "iron-crypts")

    win._repo.load.assert_called_once_with("iron-crypts")
    win._design_view.load_dungeon.assert_called_once_with(dungeon)
    win._play_view.load_dungeon.assert_called_once_with(dungeon)
    win.switch_mode.assert_called_once_with("design")


def test_open_dungeon_does_nothing_when_cancelled():
    win = _make_window(_make_dungeon())
    win.switch_mode = MagicMock()

    win.open_dungeon(_pick_fn=lambda: None)

    win._repo.load.assert_not_called()
    win.switch_mode.assert_not_called()


def test_open_dungeon_shows_error_on_file_not_found():
    win = _make_window(_make_dungeon())
    win._repo.load.side_effect = FileNotFoundError("dungeon.json missing")
    errors = []

    win.open_dungeon(_pick_fn=lambda: "bad-name", _error_fn=errors.append)

    assert len(errors) == 1
    assert "bad-name" in errors[0]


def test_open_dungeon_shows_error_on_unexpected_exception():
    win = _make_window(_make_dungeon())
    win._repo.load.side_effect = ValueError("corrupt json")
    errors = []

    win.open_dungeon(_pick_fn=lambda: "bad-name", _error_fn=errors.append)

    assert len(errors) == 1


def test_save_dungeon_stamps_save_name_on_dungeon():
    dungeon = _make_dungeon()  # save_name starts as None
    win = _make_window(dungeon)
    with patch("dungeon_daddy.llm.context_docs.generate_all_context_docs"):
        win.save_dungeon()
    assert dungeon.meta.save_name == "Iron Crypts"


def test_open_dungeon_backfills_save_name():
    loaded = _make_dungeon()  # save_name is None in the loaded JSON
    win = _make_window(_make_dungeon())
    win._repo.load.return_value = loaded
    win.switch_mode = MagicMock()

    win.open_dungeon(_pick_fn=lambda: "iron-crypts")

    assert loaded.meta.save_name == "iron-crypts"


# ---------------------------------------------------------------------------
# validate — TR-4
# ---------------------------------------------------------------------------

_VALIDATE = "dungeon_daddy.data.models.validate_dungeon"
_AUTO_FIX = "dungeon_daddy.data.models.auto_fix_dungeon"


def _make_fixable_dungeon():
    """Mock dungeon with one loop that has no explanation (fixable=1)."""
    loop = MagicMock()
    loop.explanation = ""
    loop.type = "main"
    level = MagicMock()
    level.loops = [loop]
    dungeon = MagicMock()
    dungeon.levels = [level]
    return dungeon


def test_validate_no_dungeon_shows_info():
    win = _make_window(None)
    infos = []
    win._show_info = lambda title, msg: infos.append(msg)

    win.validate()

    assert any("No dungeon loaded" in m for m in infos)


def test_validate_valid_dungeon_shows_valid():
    win = _make_window(_make_dungeon())
    infos = []
    win._show_info = lambda title, msg: infos.append(msg)

    with patch(_VALIDATE, return_value=ValidationResult(is_valid=True)):
        win.validate()

    assert any("valid" in m.lower() for m in infos)


def test_validate_auto_fix_confirmed_all_fixed_shows_all_fixed():
    dungeon = _make_fixable_dungeon()
    win = _make_window(dungeon)
    win._ask_yes_no = MagicMock(return_value=True)
    infos = []
    win._show_info = lambda title, msg: infos.append(msg)

    with patch(_VALIDATE, side_effect=[
        ValidationResult(is_valid=False, errors=["loop missing explanation"]),
        ValidationResult(is_valid=True, errors=[]),
    ]), patch(_AUTO_FIX, return_value=["Fixed: loop explanation"]) as mock_fix:
        win.validate()

    mock_fix.assert_called_once_with(dungeon)
    assert any("All errors fixed" in m for m in infos)


def test_validate_auto_fix_confirmed_remaining_errors_shows_partial_fix():
    dungeon = _make_fixable_dungeon()
    win = _make_window(dungeon)
    win._ask_yes_no = MagicMock(return_value=True)
    infos = []
    win._show_info = lambda title, msg: infos.append(msg)

    with patch(_VALIDATE, side_effect=[
        ValidationResult(is_valid=False, errors=["E1", "E2"]),
        ValidationResult(is_valid=False, errors=["E2"]),
    ]), patch(_AUTO_FIX, return_value=["Fixed E1"]) as mock_fix:
        win.validate()

    mock_fix.assert_called_once_with(dungeon)
    assert any("Applied" in m for m in infos)
    assert any("E2" in m for m in infos)


def test_validate_auto_fix_declined_shows_errors_without_fixing():
    dungeon = _make_fixable_dungeon()
    win = _make_window(dungeon)
    win._ask_yes_no = MagicMock(return_value=False)
    infos = []
    win._show_info = lambda title, msg: infos.append(msg)

    with patch(_VALIDATE, return_value=ValidationResult(is_valid=False, errors=["E1"])), \
         patch(_AUTO_FIX) as mock_fix:
        win.validate()

    mock_fix.assert_not_called()
    assert any("error(s) found" in m for m in infos)


def test_validate_no_fixable_errors_shows_errors_without_prompting():
    loop = MagicMock()
    loop.explanation = "some explanation"
    loop.type = "main"
    level = MagicMock()
    level.loops = [loop]
    dungeon = MagicMock()
    dungeon.levels = [level]

    win = _make_window(dungeon)
    ask_calls = []
    win._ask_yes_no = lambda *a: ask_calls.append(a) or False
    infos = []
    win._show_info = lambda title, msg: infos.append(msg)

    with patch(_VALIDATE, return_value=ValidationResult(is_valid=False, errors=["E1"])):
        win.validate()

    assert len(ask_calls) == 0
    assert any("error(s) found" in m for m in infos)
