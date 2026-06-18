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
    win._repo._dir = None
    win._dungeon_repo = MagicMock()
    win._save_repo = MagicMock()
    win._save_repo._dir = None
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
    win._dungeon_repo.save.assert_called_once_with(win._design_view._dungeon, "Iron Crypts")


def test_save_dungeon_uses_save_name_when_set():
    win = _make_window(_make_dungeon(save_name="iron-crypts"))
    with patch("dungeon_daddy.llm.context_docs.generate_all_context_docs"):
        win.save_dungeon()
    win._dungeon_repo.save.assert_called_once_with(win._design_view._dungeon, "iron-crypts")


def test_save_dungeon_context_docs_use_dungeon_repo():
    win = _make_window(_make_dungeon())
    captured: dict = {}

    def capture(dungeon, name, repo):
        captured["repo"] = repo

    with patch("dungeon_daddy.llm.context_docs.generate_all_context_docs", side_effect=capture):
        win.save_dungeon()

    assert captured["repo"] is win._dungeon_repo


def test_save_dungeon_stamps_save_name_on_dungeon():
    dungeon = _make_dungeon()  # save_name starts as None
    win = _make_window(dungeon)
    with patch("dungeon_daddy.llm.context_docs.generate_all_context_docs"):
        win.save_dungeon()
    assert dungeon.meta.save_name == "Iron Crypts"


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


# ---------------------------------------------------------------------------
# IP-4: model configurable via environment variable
# ---------------------------------------------------------------------------

def test_get_model_id_returns_default_when_env_not_set(monkeypatch):
    monkeypatch.delenv("DUNGEON_DADDY_MODEL", raising=False)
    from dungeon_daddy.window import _get_model_id
    assert _get_model_id() == "gpt-4o"


def test_get_model_id_reads_dungeon_daddy_model_env(monkeypatch):
    monkeypatch.setenv("DUNGEON_DADDY_MODEL", "gpt-4o-mini")
    from dungeon_daddy.window import _get_model_id
    assert _get_model_id() == "gpt-4o-mini"


def test_build_dm_agent_passes_model_id_to_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNGEON_DADDY_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("dungeon_daddy.llm.openai_provider.OpenAIProvider") as MockProvider, \
         patch("dungeon_daddy.llm.agents.dm_agent.DungeonMasterAgent"), \
         patch("dungeon_daddy.llm.telemetry.ObservingProvider"):
        from dungeon_daddy.window import _build_dm_agent
        _build_dm_agent(tmp_path / "llm_calls.jsonl")
    MockProvider.assert_called_once_with(model="gpt-4o-mini")


# ---------------------------------------------------------------------------
# launch_save_game — Slice 5
# ---------------------------------------------------------------------------

def test_launch_save_game_loads_dungeon_from_save_repo():
    dungeon = _make_dungeon(save_name="my-save")
    win = _make_window(dungeon)
    win._save_repo.load.return_value = dungeon
    win.switch_mode = MagicMock()

    win.launch_save_game("my-save")

    win._save_repo.load.assert_called_once_with("my-save")


def test_launch_save_game_sets_play_view_session_repo():
    dungeon = _make_dungeon(save_name="my-save")
    win = _make_window(dungeon)
    win._save_repo.load.return_value = dungeon
    win.switch_mode = MagicMock()

    win.launch_save_game("my-save")

    win._play_view.set_session_repo.assert_called_once_with(win._save_repo)


def test_launch_save_game_calls_load_dungeon_session():
    dungeon = _make_dungeon(save_name="my-save")
    win = _make_window(dungeon)
    win._save_repo.load.return_value = dungeon
    win.switch_mode = MagicMock()

    win.launch_save_game("my-save")

    win._play_view.load_dungeon_session.assert_called_once_with(dungeon)


def test_launch_save_game_switches_to_play():
    dungeon = _make_dungeon(save_name="my-save")
    win = _make_window(dungeon)
    win._save_repo.load.return_value = dungeon
    win.switch_mode = MagicMock()

    win.launch_save_game("my-save")

    win.switch_mode.assert_called_once_with("play")


def test_launch_save_game_attaches_rpg_context_from_saves_dir(tmp_path):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    dungeon = _make_dungeon(save_name="my-save")
    win = _make_window(dungeon)
    win._save_repo.load.return_value = dungeon
    win._save_repo._dir = saves_dir
    win.switch_mode = MagicMock()

    win.launch_save_game("my-save")

    call_kwargs = win._play_view.set_rpg_context.call_args.kwargs
    assert call_kwargs.get("portraits_dir") == saves_dir / "my-save" / "assets" / "portraits"


# ---------------------------------------------------------------------------
# Library actions — Slice 6
# ---------------------------------------------------------------------------

def _make_window_for_library(dungeon=None):
    """Extend _make_window with library-related attributes."""
    win = _make_window(dungeon)
    win._campaign_view = MagicMock()
    win._seed_library = MagicMock()
    win._library_view = MagicMock()
    win.switch_mode = MagicMock()
    return win


def test_switch_mode_library_calls_switch_to_library():
    win = _make_window(_make_dungeon())
    win._library_view = MagicMock()
    win.show_view = MagicMock()

    win.switch_mode("library")

    assert win._mode == "library"
    win.show_view.assert_called_once_with(win._library_view)


def test_open_in_designer_loads_and_switches_to_design():
    dungeon = _make_dungeon(save_name="keep-of-ruin")
    win = _make_window_for_library(dungeon)
    win._dungeon_repo.load.return_value = dungeon

    win.open_in_designer("keep-of-ruin")

    win._dungeon_repo.load.assert_called_once_with("keep-of-ruin")
    win._design_view.load_dungeon.assert_called_once_with(dungeon)
    win.switch_mode.assert_called_once_with("design")


def test_new_seed_from_dungeon_loads_manifest_into_campaign_view():
    win = _make_window_for_library()
    from dungeon_daddy.campaign.manifest import CampaignManifest

    win.new_seed_from_dungeon("haunted-fort")

    win._campaign_view.set_seed_library.assert_called_once_with(win._seed_library)
    win._campaign_view.load_manifest.assert_called_once()
    loaded: CampaignManifest = win._campaign_view.load_manifest.call_args[0][0]
    assert loaded.dungeon_slug == "haunted-fort"
    win.switch_mode.assert_called_once_with("campaign")


def test_new_seed_from_dungeon_sets_dungeon_on_campaign_view():
    dungeon = _make_dungeon(save_name="haunted-fort")
    win = _make_window_for_library(dungeon)
    win._dungeon_repo.load.return_value = dungeon

    win.new_seed_from_dungeon("haunted-fort")

    win._dungeon_repo.load.assert_called_with("haunted-fort")
    win._campaign_view.set_dungeon.assert_called_once_with(dungeon)


def test_edit_seed_loads_seed_and_switches_to_campaign():
    win = _make_window_for_library()
    win._campaign_view.attached_dungeon_slug = None

    win.edit_seed("undead-lords")

    win._campaign_view.set_seed_library.assert_called_once_with(win._seed_library)
    win._campaign_view.load_seed.assert_called_once_with("undead-lords")
    win.switch_mode.assert_called_once_with("campaign")


def test_edit_seed_sets_dungeon_when_manifest_has_dungeon_slug():
    dungeon = _make_dungeon(save_name="haunted-fort")
    win = _make_window_for_library(dungeon)
    win._dungeon_repo.load.return_value = dungeon
    win._campaign_view.attached_dungeon_slug = "haunted-fort"

    win.edit_seed("undead-lords")

    win._dungeon_repo.load.assert_called_with("haunted-fort")
    win._campaign_view.set_dungeon.assert_called_once_with(dungeon)


def test_publish_and_play_calls_publish_then_launch(tmp_path):
    win = _make_window_for_library()
    win.launch_save_game = MagicMock()
    win._dungeon_repo._dir = tmp_path / "dungeons"
    win._save_repo._dir = tmp_path / "saves"
    win.switch_mode = MagicMock()

    with patch("dungeon_daddy.campaign.publish.publish_save") as mock_pub:
        win.publish_and_play("bone-cathedral")

    mock_pub.assert_called_once()
    call_kwargs = mock_pub.call_args.kwargs
    assert call_kwargs["save_slug"] == "bone-cathedral"
    win.launch_save_game.assert_called_once_with("bone-cathedral")


def test_delete_save_removes_directory(tmp_path):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    (saves_dir / "old-run").mkdir()
    win = _make_window_for_library()
    win._save_repo._dir = saves_dir

    win.delete_save("old-run")

    assert not (saves_dir / "old-run").exists()


def test_delete_save_does_nothing_when_slug_missing(tmp_path):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    win = _make_window_for_library()
    win._save_repo._dir = saves_dir

    win.delete_save("nonexistent")  # should not raise
