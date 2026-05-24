"""Non-Windows platform stub — all operations raise NotImplementedError."""
from __future__ import annotations

_MSG = "UI smoke tests require Windows. Contribute a platform backend for your OS."


def set_dpi_awareness() -> None:
    raise NotImplementedError(_MSG)


def find_window(title: str) -> int:
    raise NotImplementedError(_MSG)


def get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    raise NotImplementedError(_MSG)


def get_system_metrics(index: int) -> int:
    raise NotImplementedError(_MSG)


def set_window_pos(hwnd: int, x: int, y: int, flags: int) -> None:
    raise NotImplementedError(_MSG)


def post_message(hwnd: int, msg: int, wparam: int, lparam: int) -> None:
    raise NotImplementedError(_MSG)


def set_cursor_pos(x: int, y: int) -> None:
    raise NotImplementedError(_MSG)


def mouse_event(flags: int, x: int, y: int, data: int, extra: int) -> None:
    raise NotImplementedError(_MSG)


def send_click(sx: int, sy: int, delay: float = 0.05) -> None:
    raise NotImplementedError(_MSG)


def send_key_combo(*vks: int) -> None:
    raise NotImplementedError(_MSG)


def send_scroll(sx: int, sy: int, clicks: int = 3) -> None:
    raise NotImplementedError(_MSG)


def send_text(text: str, delay: float = 0.02) -> None:
    raise NotImplementedError(_MSG)


def get_dpi_scale(hwnd: int = 0) -> float:
    raise NotImplementedError(_MSG)
