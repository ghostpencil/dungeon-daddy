"""Thread lifecycle contract for DesignView.

Tests that _llm_busy guard works with real threads (not mocked threading).
Mirrors the pattern in test_play_view_threading.py.
"""
from __future__ import annotations

import os
import queue
import time
from unittest.mock import MagicMock, patch

from dungeon_daddy.data.models import DesignMode, Dungeon, DungeonMeta
from dungeon_daddy.llm.agents.design_agent import DesignAgent
from dungeon_daddy.llm.agents.wizard_agent import DungeonWizardAgent
from dungeon_daddy.views.design_view import DesignView

# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------

class _SlowProvider:
    """Blocks for 100 ms then returns a fixed string. Counts calls."""

    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, messages, system: str = "", max_tokens: int = 1024) -> str:
        self.call_count += 1
        time.sleep(0.1)
        return "Tell me more about your theme."

    @property
    def model_id(self) -> str:
        return "slow-stub"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _make_view(wizard_provider=None, design_provider=None) -> DesignView:
    """Create a DesignView without arcade initialisation."""
    view = DesignView.__new__(DesignView)
    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._design_mode = DesignMode.WIZARD
    view._wizard_history = []
    view._design_history = []
    view._brief = None
    view._current_level_brief = None
    view._current_level = 1
    view._generation_retries = 0
    view._context_overwrite_confirmed = False
    view._awaiting_name_choice = False
    view._dungeon = Dungeon(
        meta=DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q"),
        levels=[],
    )
    view._chat = MagicMock()
    view._tree = MagicMock()
    view._inspector = MagicMock()
    view._repo = MagicMock()
    view._repo.load_context_doc.return_value = ""
    view._wizard_agent = (
        DungeonWizardAgent(wizard_provider, loop_patterns={})
        if wizard_provider is not None
        else MagicMock()
    )
    view._generator_agent = MagicMock()
    view._design_agent = (
        DesignAgent(design_provider)
        if design_provider is not None
        else MagicMock()
    )
    return view


# ---------------------------------------------------------------------------
# Tests — wizard mode
# ---------------------------------------------------------------------------

def test_busy_flag_cleared_after_wizard_thread_completes():
    """_llm_busy is False after the wizard thread finishes (cleared in finally)."""
    provider = _SlowProvider()
    view = _make_view(wizard_provider=provider)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        view._on_chat_send("hello")

    assert view._active_thread is not None
    view._active_thread.join(timeout=5.0)

    assert view._llm_busy is False


def test_second_wizard_send_dropped_while_busy():
    """A second _on_chat_send while the wizard thread runs is silently dropped."""
    provider = _SlowProvider()
    view = _make_view(wizard_provider=provider)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        view._on_chat_send("first message")   # spawns thread, _llm_busy = True
        view._on_chat_send("second message")  # dropped — busy

    view._active_thread.join(timeout=5.0)

    assert provider.call_count == 1


# ---------------------------------------------------------------------------
# Tests — edit mode
# ---------------------------------------------------------------------------

def test_busy_flag_cleared_after_edit_chat_thread_completes():
    """_llm_busy is False after the design-chat thread finishes (cleared in finally)."""
    provider = _SlowProvider()
    view = _make_view(design_provider=provider)
    view._design_mode = DesignMode.EDIT

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        view._on_chat_send("refine the layout")

    assert view._active_thread is not None
    view._active_thread.join(timeout=5.0)

    assert view._llm_busy is False
