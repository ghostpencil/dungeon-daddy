"""Integration tests for tools/ui_harness.py.

Each test launches the real app — expect ~8 s per test.
Run with: pytest tests/integration/test_ui_harness.py -v
"""
import pytest
from ui_harness import UITestHarness

# ---------------------------------------------------------------------------
# Behavior 1: entering the context manager launches the app and exposes
#             window_rect
# ---------------------------------------------------------------------------

def test_harness_enters_and_finds_window():
    with UITestHarness(tag="harness_test") as h:
        assert h.window_rect is not None
        left, top, right, bottom = h.window_rect
        assert right > left
        assert bottom > top


# ---------------------------------------------------------------------------
# Behavior 2: capture() returns a Path to an existing PNG file
# ---------------------------------------------------------------------------

def test_capture_returns_existing_png():
    with UITestHarness(tag="harness_test") as h:
        path = h.capture("snap")
        assert path.exists()
        assert path.suffix == ".png"


# ---------------------------------------------------------------------------
# Behavior 3: screenshot filename contains the harness tag
# ---------------------------------------------------------------------------

def test_capture_filename_contains_tag():
    with UITestHarness(tag="mytag") as h:
        path = h.capture()
        assert "mytag" in path.name


# ---------------------------------------------------------------------------
# Behavior 4: app process is not running after __exit__
# ---------------------------------------------------------------------------

def test_app_is_terminated_after_exit():
    import ctypes
    with UITestHarness(tag="harness_test") as h:
        assert h.window_rect is not None

    hwnd = ctypes.windll.user32.FindWindowW(None, "Dungeon Daddy")
    assert hwnd == 0, "Window still present after harness __exit__"


# ---------------------------------------------------------------------------
# Behavior 5: cleanup runs even when the with-body raises
# ---------------------------------------------------------------------------

def test_cleanup_runs_on_exception():
    import ctypes
    with pytest.raises(RuntimeError):
        with UITestHarness(tag="harness_test") as h:
            assert h.window_rect is not None
            raise RuntimeError("simulated test failure")

    hwnd = ctypes.windll.user32.FindWindowW(None, "Dungeon Daddy")
    assert hwnd == 0, "Window still present after exception in with-body"
