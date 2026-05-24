import queue
from unittest.mock import MagicMock, patch

from dungeon_daddy.data.models import DesignMode, Dungeon, DungeonMeta, Level
from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief
from dungeon_daddy.views.design_view import DesignView, LLMResult


# ---------------------------------------------------------------------------
# LLMResult dataclass
# ---------------------------------------------------------------------------

def test_llm_result_defaults():
    result = LLMResult(content="hello")
    assert result.content == "hello"
    assert result.error is None
    assert result.result_type == "chat"


def test_llm_result_type_variants():
    assert LLMResult(content="", result_type="wizard").result_type == "wizard"
    assert LLMResult(content="", result_type="level").result_type == "level"
    assert LLMResult(content="", result_type="chat").result_type == "chat"


def test_llm_result_error_field():
    result = LLMResult(content="", error="timeout")
    assert result.error == "timeout"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dungeon() -> Dungeon:
    return Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q"),
        levels=[],
    )


def _make_level(level_id: int = 1) -> Level:
    return Level(
        id=level_id, name="Level", summary="", ecology="", loop="",
        width=10, height=10, entries=[], rooms=[], connections=[],
    )


def _make_brief(**kw) -> DungeonBrief:
    defaults = dict(
        title="Crypt of Doom", theme="gothic", setting="underground",
        party="4 heroes", quest="slay the lich", num_levels=2, gm_notes="",
    )
    defaults.update(kw)
    return DungeonBrief(**defaults)


def _make_view() -> DesignView:
    """Create a DesignView without arcade initialisation."""
    view = DesignView.__new__(DesignView)
    view._result_queue = queue.Queue()
    view._llm_busy = True
    view._dungeon = MagicMock()
    view._wizard_agent = MagicMock()
    view._generator_agent = MagicMock()
    view._design_agent = MagicMock()
    view._chat = MagicMock()
    view._tree = MagicMock()
    view._inspector = MagicMock()
    view._design_mode = DesignMode.WIZARD
    view._brief = None
    view._current_level_brief = None
    view._current_level = 1
    view._generation_retries = 0
    view._active_thread = None
    view._wizard_history = []
    view._design_history = []
    view._repo = MagicMock()
    view._repo.load_context_doc.return_value = ""
    view._context_overwrite_confirmed = False
    view._awaiting_name_choice = False
    return view


# ---------------------------------------------------------------------------
# _run_llm
# ---------------------------------------------------------------------------

def test_run_llm_puts_wizard_result():
    view = _make_view()
    view._wizard_agent = MagicMock()
    view._wizard_agent.chat.return_value = "What theme do you prefer?"

    view._run_llm(history=[])

    result = view._result_queue.get_nowait()
    assert result.result_type == "wizard"
    assert result.content == "What theme do you prefer?"
    assert result.error is None


def test_run_llm_puts_error_result_on_exception():
    view = _make_view()
    view._wizard_agent = MagicMock()
    view._wizard_agent.chat.side_effect = RuntimeError("network down")

    view._run_llm(history=[])

    result = view._result_queue.get_nowait()
    assert result.result_type == "wizard"
    assert result.error == "network down"


def test_run_llm_clears_busy_flag():
    view = _make_view()
    view._wizard_agent = MagicMock()
    view._wizard_agent.chat.return_value = "ok"

    view._run_llm(history=[])

    assert view._llm_busy is False


# ---------------------------------------------------------------------------
# _run_generation
# ---------------------------------------------------------------------------

def test_run_generation_puts_level_result():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._brief = _make_brief()
    view._generator_agent = MagicMock()
    view._generator_agent.generate_level.return_value = '```json\n{"id": 1}\n```'
    level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")

    view._run_generation(level_brief=level_brief)

    result = view._result_queue.get_nowait()
    assert result.result_type == "level"
    assert result.content == '```json\n{"id": 1}\n```'
    assert result.error is None


def test_run_generation_puts_error_result_on_exception():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._brief = _make_brief()
    view._generator_agent = MagicMock()
    view._generator_agent.generate_level.side_effect = ValueError("bad json")
    level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")

    view._run_generation(level_brief=level_brief)

    result = view._result_queue.get_nowait()
    assert result.result_type == "level"
    assert result.error == "bad json"


def test_run_generation_clears_busy_flag():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._brief = _make_brief()
    view._generator_agent = MagicMock()
    view._generator_agent.generate_level.return_value = "response"
    level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")

    view._run_generation(level_brief=level_brief)

    assert view._llm_busy is False


def test_run_generation_passes_level_brief_to_agent():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._brief = _make_brief()
    view._generator_agent = MagicMock()
    view._generator_agent.generate_level.return_value = "response"
    level_brief = LevelBrief(level_number=2, ecology="cave", main_loop_pattern="lollipop")
    errors = ["missing room A", "invalid connection"]

    view._run_generation(level_brief=level_brief, errors=errors)

    view._generator_agent.generate_level.assert_called_once_with(
        view._brief, level_brief, view._dungeon, errors
    )


# ---------------------------------------------------------------------------
# _run_design_chat
# ---------------------------------------------------------------------------

def test_run_design_chat_puts_chat_result():
    view = _make_view()
    view._design_agent = MagicMock()
    view._design_agent.chat.return_value = "Move the boss to room 5."

    view._run_design_chat(history=[], dungeon=view._dungeon)

    result = view._result_queue.get_nowait()
    assert result.result_type == "chat"
    assert result.content == "Move the boss to room 5."
    assert result.error is None


def test_run_design_chat_puts_error_result_on_exception():
    view = _make_view()
    view._design_agent = MagicMock()
    view._design_agent.chat.side_effect = RuntimeError("api error")

    view._run_design_chat(history=[], dungeon=view._dungeon)

    result = view._result_queue.get_nowait()
    assert result.result_type == "chat"
    assert result.error == "api error"


def test_run_design_chat_clears_busy_flag():
    view = _make_view()
    view._design_agent = MagicMock()
    view._design_agent.chat.return_value = "ok"

    view._run_design_chat(history=[], dungeon=view._dungeon)

    assert view._llm_busy is False


# ---------------------------------------------------------------------------
# on_update — queue drain dispatch
# ---------------------------------------------------------------------------

def test_on_update_chat_result_adds_dm_message():
    view = _make_view()
    view._result_queue.put(LLMResult(content="Nice dungeon!", result_type="chat"))

    view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "Nice dungeon!")


def test_on_update_chat_error_adds_error_message():
    view = _make_view()
    view._result_queue.put(LLMResult(content="", error="api error", result_type="chat"))

    view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "⚠ api error")


def test_on_update_wizard_result_no_brief_adds_message_only():
    view = _make_view()
    view._wizard_agent.parse_brief.return_value = None
    view._wizard_agent.parse_level_brief.return_value = None
    view._result_queue.put(LLMResult(content="Tell me the theme.", result_type="wizard"))

    view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "Tell me the theme.")
    assert view._design_mode == DesignMode.WIZARD


def test_on_update_wizard_result_with_brief_switches_to_level_wizard():
    view = _make_view()
    brief = _make_brief(num_levels=3)
    view._wizard_agent.parse_brief.return_value = brief

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```brief\n...\n```", result_type="wizard"))
        view.on_update(0.0)

    assert view._design_mode == DesignMode.LEVEL_WIZARD
    assert view._llm_busy is True
    mock_thread.assert_called_once()


def test_on_update_wizard_level_brief_fires_generation():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._design_mode = DesignMode.LEVEL_WIZARD
    view._brief = _make_brief(num_levels=2)
    view._dungeon = _make_dungeon()
    level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")
    view._wizard_agent.parse_brief.return_value = None
    view._wizard_agent.parse_level_brief.return_value = level_brief

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```level_brief\n...\n```", result_type="wizard"))
        view.on_update(0.0)

    assert view._llm_busy is True
    mock_thread.assert_called_once()
    assert view._current_level_brief is level_brief


def test_on_update_wizard_error_adds_error_message():
    view = _make_view()
    view._result_queue.put(LLMResult(content="", error="timeout", result_type="wizard"))

    view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "⚠ timeout")
    assert view._design_mode == DesignMode.WIZARD


def test_on_update_level_result_accepted_appends_to_dungeon():
    from dungeon_daddy.data.models import ValidationResult
    view = _make_view()
    brief = _make_brief(num_levels=2)
    view._brief = brief
    view._dungeon = _make_dungeon()
    view._current_level = 1
    level = _make_level()
    view._generator_agent.parse_level.return_value = level

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate, \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_validate.return_value = ValidationResult(is_valid=True)
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    view._tree.set_dungeon.assert_called_once()
    assert level in view._dungeon.levels


def test_on_update_level_result_non_last_stays_in_level_wizard():
    from dungeon_daddy.data.models import ValidationResult
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._design_mode = DesignMode.LEVEL_WIZARD
    brief = _make_brief(num_levels=3)
    view._brief = brief
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._current_level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")
    view._generator_agent.parse_level.return_value = _make_level()

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate:
        mock_validate.return_value = ValidationResult(is_valid=True)
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    # Stays in level_wizard, waits for GM input before kicking next level
    assert view._design_mode == DesignMode.LEVEL_WIZARD


def test_on_update_level_result_last_level_activates_edit_mode():
    from dungeon_daddy.data.models import ValidationResult
    view = _make_view()
    brief = _make_brief(num_levels=1)
    view._brief = brief
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._generator_agent.parse_level.return_value = _make_level()

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate:
        mock_validate.return_value = ValidationResult(is_valid=True)
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    assert view._design_mode == DesignMode.EDIT


def test_on_update_level_result_validation_errors_shows_revising():
    from dungeon_daddy.data.models import ValidationResult
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    brief = _make_brief(num_levels=2)
    view._brief = brief
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._current_level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")
    view._generation_retries = 0
    view._generator_agent.parse_level.return_value = _make_level()

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate, \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_validate.return_value = ValidationResult(is_valid=False, errors=["bad room"])
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "Revising level 1…")
    assert view._generation_retries == 1


def test_on_update_level_result_parse_error_retries_with_error():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._brief = _make_brief(num_levels=1)
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._current_level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")
    view._generation_retries = 0
    view._generator_agent.parse_level.side_effect = ValueError("duplicate main_loop_role 'obstacle'")

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "Revising level 1…")
    assert view._generation_retries == 1


def test_on_update_level_result_parse_error_exhausted_shows_error():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._brief = _make_brief(num_levels=1)
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._current_level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")
    view._generation_retries = 3
    view._generator_agent.parse_level.side_effect = ValueError("duplicate main_loop_role 'obstacle'")

    view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
    view.on_update(0.0)

    calls = [str(c) for c in view._chat.add_message.call_args_list]
    assert any("duplicate main_loop_role" in c for c in calls)
    assert view._generation_retries == 3


# ---------------------------------------------------------------------------
# LLM error paths (SI-1)
# ---------------------------------------------------------------------------

def test_chat_error_result_shows_error_bubble():
    view = _make_view()
    view._result_queue.put(LLMResult(content="", error="rate limit", result_type="chat"))

    view.on_update(0.0)

    view._chat.add_message.assert_called_once_with("dm", "⚠ rate limit")
    view._chat.set_busy.assert_called_with(False)


def test_wizard_error_result_shows_error_bubble():
    view = _make_view()
    view._result_queue.put(LLMResult(content="", error="rate limit", result_type="wizard"))

    view.on_update(0.0)

    view._chat.add_message.assert_called_once_with("dm", "⚠ rate limit")
    view._chat.set_busy.assert_called_with(False)


def test_level_error_result_shows_error_bubble():
    view = _make_view()
    view._result_queue.put(LLMResult(content="", error="rate limit", result_type="level"))

    view.on_update(0.0)

    view._chat.add_message.assert_called_once_with("dm", "⚠ Level 1: rate limit")
    view._chat.set_busy.assert_called_with(False)


def test_on_update_level_result_non_last_shows_ready_message():
    from dungeon_daddy.data.models import ValidationResult
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._design_mode = DesignMode.LEVEL_WIZARD
    brief = _make_brief(num_levels=3)
    view._brief = brief
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._current_level_brief = LevelBrief(level_number=1, ecology="cave", main_loop_pattern="lollipop")
    view._generator_agent.parse_level.return_value = _make_level()

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate, \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_validate.return_value = ValidationResult(is_valid=True)
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    view._chat.add_message.assert_any_call(
        "dm",
        "Level 1 ready! Test Drive it, or send a message when you're ready to design the next level.",
    )


def test_on_update_level_error_adds_error_message():
    view = _make_view()
    view._brief = _make_brief()
    view._current_level = 2
    view._result_queue.put(LLMResult(content="", error="timeout", result_type="level"))

    view.on_update(0.0)

    view._chat.add_message.assert_any_call("dm", "⚠ Level 2: timeout")


def test_handle_level_result_valid_expands_new_level():
    from dungeon_daddy.data.models import ValidationResult
    view = _make_view()
    view._brief = _make_brief(num_levels=2)
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._generator_agent.parse_level.return_value = _make_level()

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate:
        mock_validate.return_value = ValidationResult(is_valid=True)
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    view._tree.expand_level.assert_called_once_with(0)


# ---------------------------------------------------------------------------
# _on_chat_send — thread launch
# ---------------------------------------------------------------------------

def test_on_chat_send_wizard_mode_launches_llm_thread():
    view = _make_view()
    view._design_mode = DesignMode.WIZARD
    view._llm_busy = False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("hello")

    view._chat.add_message.assert_any_call("gm", "hello")
    assert view._llm_busy is True
    mock_thread.assert_called_once()


def test_on_chat_send_level_wizard_mode_launches_phase2_thread():
    view = _make_view()
    view._design_mode = DesignMode.LEVEL_WIZARD
    view._llm_busy = False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("cave moss, pick lollipop")

    assert view._llm_busy is True
    call_kwargs = mock_thread.call_args.kwargs
    assert call_kwargs["target"] == view._run_llm
    assert call_kwargs["kwargs"]["phase"] == 2


def test_on_chat_send_edit_mode_launches_design_chat_thread():
    view = _make_view()
    view._design_mode = DesignMode.EDIT
    view._dungeon = _make_dungeon()
    view._llm_busy = False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("move the boss")

    assert view._llm_busy is True
    mock_thread.assert_called_once()


def test_on_chat_send_ignores_when_busy():
    view = _make_view()
    view._llm_busy = True

    view._on_chat_send("hello")

    view._chat.add_message.assert_not_called()


# ---------------------------------------------------------------------------
# on_hide_view — thread join
# ---------------------------------------------------------------------------

def test_on_hide_view_joins_active_thread():
    view = _make_view()
    mock_thread = MagicMock()
    view._active_thread = mock_thread
    view._manager = MagicMock()

    view.on_hide_view()

    mock_thread.join.assert_called_once_with(timeout=3.0)


def test_on_hide_view_no_crash_without_active_thread():
    view = _make_view()
    view._active_thread = None
    view._manager = MagicMock()

    view.on_hide_view()

    view._manager.disable.assert_called_once()
    assert view._active_thread is None


# ---------------------------------------------------------------------------
# Missing API key notice
# ---------------------------------------------------------------------------

def test_on_chat_send_shows_notice_when_api_key_missing():
    view = _make_view()
    view._design_mode = DesignMode.WIZARD
    view._llm_busy = False

    with patch.dict("os.environ", {}, clear=True), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        view._on_chat_send("hello")

    view._chat.add_message.assert_any_call("dm", "⚠ OPENAI_API_KEY is not set.")
    mock_thread.assert_not_called()


def test_on_chat_send_proceeds_when_api_key_present():
    view = _make_view()
    view._design_mode = DesignMode.WIZARD
    view._llm_busy = False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("hello")

    mock_thread.assert_called_once()


# ---------------------------------------------------------------------------
# _on_loop_activated — tree highlight wiring
# ---------------------------------------------------------------------------

def test_on_loop_activated_calls_set_active_loop_with_matching_loop():
    from dungeon_daddy.data.models import Loop
    view = _make_view()
    dungeon = _make_dungeon()
    level = _make_level()
    loop = Loop(
        id="L1-main", pattern="lock_key", note="", entry="R1", goal="R3",
        path_a=["R1", "R2", "R3"], path_b=["R1", "R3"], type="main",
    )
    level.loops = [loop]
    dungeon.levels = [level]
    view._dungeon = dungeon

    view._on_loop_activated("L1-main")

    view._tree.set_active_loop.assert_called_once_with(loop)


def test_on_loop_activated_unknown_id_calls_set_active_loop_none():
    view = _make_view()
    view._dungeon = _make_dungeon()

    view._on_loop_activated("no-such-id")

    view._tree.set_active_loop.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# C-3 — Context Doc overlay
# ---------------------------------------------------------------------------

from dungeon_daddy.data.models import ContextDocType


def _make_overlay_view() -> DesignView:
    """DesignView with repo mock and overlay state initialised."""
    view = _make_view()
    view._repo = MagicMock()
    view._overlay_open = False
    view._overlay_doc_type = None
    view._overlay_dungeon_name = None
    view._overlay_level_id = None
    view._overlay_content = None
    view._overlay_widgets = []
    view._overlay_input = None
    view._ui_built = False
    view._manager = MagicMock()
    return view


def test_open_context_doc_overlay_sets_overlay_open():
    view = _make_overlay_view()
    view.open_context_doc_overlay(ContextDocType.SETTING, "my_dungeon", None, "Some text")
    assert view._overlay_open is True


def test_save_context_doc_overlay_calls_repo():
    view = _make_overlay_view()
    view.open_context_doc_overlay(ContextDocType.PARTY, "castle", None, "Old text")
    view._overlay_content = "Updated party doc."

    view.save_context_doc_overlay()

    view._repo.save_context_doc.assert_called_once_with("castle", ContextDocType.PARTY, "Updated party doc.", None)


def test_save_context_doc_overlay_closes_overlay():
    view = _make_overlay_view()
    view.open_context_doc_overlay(ContextDocType.SETTING, "crypt", None, "content")

    view.save_context_doc_overlay()

    assert view._overlay_open is False


def test_close_context_doc_overlay_does_not_save():
    view = _make_overlay_view()
    view.open_context_doc_overlay(ContextDocType.SETTING, "tomb", None, "text")

    view.close_context_doc_overlay()

    view._repo.save_context_doc.assert_not_called()
    assert view._overlay_open is False


def test_load_dungeon_pushes_word_counts_to_inspector():
    from dungeon_daddy.ui.panels.inspector_panel import ContextDocStatus
    view = _make_overlay_view()
    level = _make_level(level_id=1)
    dungeon = Dungeon(
        meta=DungeonMeta(title="The Crypt", theme="t", setting="s", party="p", quest="q"),
        levels=[level],
    )
    view._repo.load_context_doc.side_effect = lambda name, doc_type, level_id=None: {
        ContextDocType.SETTING: "word one two three",
        ContextDocType.PARTY: "",
        ContextDocType.LEVEL_DESIGN: "alpha beta",
    }[doc_type]

    view.load_dungeon(dungeon)

    statuses = view._inspector.set_context_doc_statuses.call_args[0][0]
    by_type = {s.doc_type: s for s in statuses}
    assert by_type[ContextDocType.SETTING].word_count == 4
    assert by_type[ContextDocType.PARTY].word_count is None
    assert by_type[ContextDocType.LEVEL_DESIGN].word_count == 2


# ---------------------------------------------------------------------------
# Design Chat busy indicator — mirrors Play mode loading bubble
# ---------------------------------------------------------------------------

def test_on_chat_send_wizard_mode_calls_set_busy_true():
    view = _make_view()
    view._design_mode = DesignMode.WIZARD
    view._llm_busy = False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("hello")

    view._chat.set_busy.assert_called_with(True)


def test_on_chat_send_edit_mode_calls_set_busy_true():
    view = _make_view()
    view._design_mode = DesignMode.EDIT
    view._dungeon = _make_dungeon()
    view._llm_busy = False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("redesign the boss room")

    view._chat.set_busy.assert_called_with(True)


def test_handle_chat_result_calls_set_busy_false():
    view = _make_view()
    result = LLMResult(content="Here's the updated room.", result_type="chat")

    view._handle_chat_result(result)

    view._chat.set_busy.assert_called_with(False)


def test_handle_wizard_result_error_calls_set_busy_false():
    view = _make_view()
    result = LLMResult(content="", error="timeout", result_type="wizard")

    view._handle_wizard_result(result)

    view._chat.set_busy.assert_called_with(False)


def test_on_mouse_press_routes_tree_click():
    view = _make_view()
    view._overlay_open = False
    view._menu_bar = MagicMock()
    view._menu_bar.handle_click.return_value = False
    view._chat.on_mouse_press.return_value = False
    view._inspector.on_mouse_press.return_value = False
    view._inspector.hit_test_drive.return_value = False
    view._inspector.hit_start_play.return_value = False
    view._tree.handle_click.return_value = True
    view.window = MagicMock()

    view.on_mouse_press(10, 200, 1, 0)

    view._tree.handle_click.assert_called_once_with(10, 200)


# ---------------------------------------------------------------------------
# CD-4 — Incremental context doc writes during wizard
# ---------------------------------------------------------------------------

def test_start_generation_writes_setting_and_party_docs():
    from dungeon_daddy.data.models import ContextDocType
    view = _make_view()
    brief = _make_brief(title="Iron Halls", theme="Stone", setting="A dark keep.",
                        party="Warriors", quest="Find the gem", num_levels=1)

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._start_generation(brief)

    saved_types = {call.args[1] for call in view._repo.save_context_doc.call_args_list}
    assert ContextDocType.SETTING in saved_types
    assert ContextDocType.PARTY in saved_types


def test_start_generation_refreshes_context_doc_statuses():
    view = _make_view()
    brief = _make_brief()

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._start_generation(brief)

    view._inspector.set_context_doc_statuses.assert_called()


def test_handle_level_result_writes_level_design_doc_on_valid_level():
    from dungeon_daddy.data.models import ValidationResult, ContextDocType
    view = _make_view()
    view._brief = _make_brief(num_levels=2)
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._generator_agent.parse_level.return_value = _make_level(level_id=1)

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate:
        mock_validate.return_value = ValidationResult(is_valid=True)
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    saved_types = {call.args[1] for call in view._repo.save_context_doc.call_args_list}
    assert ContextDocType.LEVEL_DESIGN in saved_types


# ---------------------------------------------------------------------------
# CD-5 — Overwrite-or-rename prompt
# ---------------------------------------------------------------------------

def test_start_generation_prompts_when_setting_doc_exists():
    """If setting.md pre-exists and overwrite not confirmed, post prompt and return early."""
    view = _make_view()
    view._llm_busy = False
    brief = _make_brief(title="Iron Halls")
    view._repo.load_context_doc.return_value = "# Iron Halls\nExisting setting."

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        view._start_generation(brief)

    view._chat.add_message.assert_called()
    assert view._awaiting_name_choice is True
    view._repo.save_context_doc.assert_not_called()
    mock_thread.assert_not_called()


def test_on_chat_send_overwrite_sets_flag_and_proceeds():
    """GM types 'overwrite' → confirmed flag set, docs written, thread launched."""
    view = _make_view()
    view._llm_busy = False
    view._awaiting_name_choice = True
    view._brief = _make_brief(title="Iron Halls")
    view._dungeon = _make_dungeon()

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("overwrite")

    assert view._context_overwrite_confirmed is True
    assert view._awaiting_name_choice is False
    view._repo.save_context_doc.assert_called()
    mock_thread.assert_called_once()


def test_on_chat_send_new_name_sets_save_name_and_proceeds():
    """GM types a new name → meta.save_name updated, docs written, thread launched."""
    view = _make_view()
    view._llm_busy = False
    view._awaiting_name_choice = True
    view._brief = _make_brief(title="Iron Halls")
    view._dungeon = _make_dungeon()

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._on_chat_send("iron_halls_v2")

    assert view._dungeon.meta.save_name == "iron_halls_v2"
    assert view._awaiting_name_choice is False
    view._repo.save_context_doc.assert_called()
    mock_thread.assert_called_once()


def test_start_generation_skips_prompt_when_overwrite_confirmed():
    """Second dungeon in same session: overwrite confirmed, prompt skipped."""
    view = _make_view()
    view._llm_busy = False
    view._context_overwrite_confirmed = True
    brief = _make_brief(title="Second Dungeon")
    view._repo.load_context_doc.return_value = "Existing setting doc."

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._start_generation(brief)

    assert view._awaiting_name_choice is False
    mock_thread.assert_called_once()
    view._repo.save_context_doc.assert_called()


# ---------------------------------------------------------------------------
# F-31 — Test Drive vs. Start Play routing (Step 4a)
# ---------------------------------------------------------------------------

def _make_routable_view() -> DesignView:
    view = _make_view()
    view._overlay_open = False
    view._menu_bar = MagicMock()
    view._menu_bar.handle_click.return_value = False
    view._tree.handle_click.return_value = False
    view._chat.on_mouse_press.return_value = False
    view._inspector.on_mouse_press.return_value = False
    view.window = MagicMock()
    return view


def test_test_drive_click_calls_launch_test_drive():
    view = _make_routable_view()
    dungeon = _make_dungeon()
    dungeon.levels = [_make_level()]
    view._dungeon = dungeon
    view._inspector.hit_test_drive.return_value = True
    view._inspector.hit_start_play.return_value = False

    view.on_mouse_press(10, 100, 1, 0)

    view.window.launch_test_drive.assert_called_once_with(dungeon)
    view.window.launch_play_session.assert_not_called()


def test_start_play_click_calls_launch_play_session():
    view = _make_routable_view()
    dungeon = _make_dungeon()
    dungeon.meta.save_name = "crypt"
    dungeon.levels = [_make_level()]
    view._dungeon = dungeon
    view._inspector.hit_test_drive.return_value = False
    view._inspector.hit_start_play.return_value = True

    view.on_mouse_press(10, 100, 1, 0)

    view.window.launch_play_session.assert_called_once_with(dungeon)



def test_refresh_play_button_state_on_load():
    view = _make_overlay_view()
    dungeon = _make_dungeon()
    dungeon.levels = [_make_level(level_id=1)]
    view._repo.load_context_doc.return_value = ""
    view._repo.load_session.return_value = None

    view.load_dungeon(dungeon)

    view._inspector.set_saved_state.assert_called()


# ---------------------------------------------------------------------------
# SI-3 — Design view state mutations (assert fields directly)
# ---------------------------------------------------------------------------

def test_wizard_result_populates_brief():
    brief = _make_brief(title="Crypt of Doom")
    view = _make_view()
    view._brief = None
    view._wizard_agent.parse_brief.return_value = brief
    view._result_queue.put(LLMResult(content="```brief\n...\n```", result_type="wizard"))

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view.on_update(0.0)

    assert view._brief is not None
    assert view._brief.title == "Crypt of Doom"


def test_wizard_level_brief_sets_current_level():
    from dungeon_daddy.llm.agents.wizard_agent import LevelBrief
    view = _make_view()
    view._design_mode = DesignMode.LEVEL_WIZARD
    view._brief = _make_brief(num_levels=3)
    view._dungeon = _make_dungeon()
    level_brief = LevelBrief(level_number=2, ecology="swamp", main_loop_pattern="lollipop")
    view._wizard_agent.parse_brief.return_value = None
    view._wizard_agent.parse_level_brief.return_value = level_brief

    with patch("dungeon_daddy.views.design_view.threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        view._result_queue.put(LLMResult(content="```level_brief\n...\n```", result_type="wizard"))
        view.on_update(0.0)

    assert view._current_level == 2


def test_level_result_success_resets_retries():
    from dungeon_daddy.data.models import ValidationResult
    view = _make_view()
    view._brief = _make_brief(num_levels=2)
    view._dungeon = _make_dungeon()
    view._current_level = 1
    view._generation_retries = 2
    view._generator_agent.parse_level.return_value = _make_level()

    with patch("dungeon_daddy.views.design_view.validate_dungeon") as mock_validate:
        mock_validate.return_value = ValidationResult(is_valid=True)
        view._result_queue.put(LLMResult(content="```json\n{}\n```", result_type="level"))
        view.on_update(0.0)

    assert view._generation_retries == 0
