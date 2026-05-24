import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

from smoke_helpers import check_no_error_dialog, pixel_rgb


def _make_buffer(shot_w: int, height: int) -> bytearray:
    return bytearray(height * shot_w * 4)


def _plant_white_block(buf: bytearray, shot_w: int, col: int, row: int, size: int = 30) -> None:
    for dr in range(size):
        for dc in range(size):
            offset = ((row + dr) * shot_w + (col + dc)) * 4
            buf[offset]     = 255  # B
            buf[offset + 1] = 255  # G
            buf[offset + 2] = 255  # R
            buf[offset + 3] = 255  # A


def test_check_no_error_dialog_detects_block_past_1400():
    # col=1452 is past the old WINDOW_W=1400 limit and lands on a scan-grid start
    # (scan positions: x_start=12, step=30 → 12, 42, …, 1332[old last], 1362, …, 1452, …)
    # row=44 is y_start (win_top + OS_TITLEBAR_H + border = 0+32+12)
    # Together they ensure the block is fully inside one 30×30 scan cell.
    shot_w = 1750
    win_left, win_top, win_right, win_bottom = 0, 0, 1750, 1165

    buf = _make_buffer(shot_w, win_bottom)
    _plant_white_block(buf, shot_w, col=1452, row=44)

    result = check_no_error_dialog(bytes(buf), shot_w,
                                   win_left, win_top, win_right, win_bottom)
    assert result == 1


def test_check_no_error_dialog_clean_window_passes():
    shot_w = 1750
    win_left, win_top, win_right, win_bottom = 0, 0, 1750, 1165
    buf = _make_buffer(shot_w, win_bottom)
    result = check_no_error_dialog(bytes(buf), shot_w,
                                   win_left, win_top, win_right, win_bottom)
    assert result == 0


def test_pixel_rgb_at_125_scale():
    # Physical pixel for Arcade (100, 800) at 1.25× scale, window at (0, 0):
    #   px = int(100 * 1.25 + 0.5) = 125
    #   py = int(32 * 1.25 + 0.5) + int((900 - 800) * 1.25 + 0.5) = 40 + 125 = 165
    shot_w = 1750
    pixels = bytearray(200 * shot_w * 4)
    offset = (165 * shot_w + 125) * 4
    pixels[offset]     = 128   # B
    pixels[offset + 1] = 0     # G
    pixels[offset + 2] = 255   # R
    pixels[offset + 3] = 255   # A

    with patch("smoke_helpers._s", return_value=1.25):
        r, g, b = pixel_rgb(bytes(pixels), shot_w, 0, 0, 100, 800)

    assert (r, g, b) == (255, 0, 128)


def test_check_no_error_dialog_nonzero_window_origin():
    # Verify bounds math is correct when the window is not at (0, 0).
    # Block placed at (x_start, y_start) = (win_left+border, win_top+OS_TITLEBAR_H+border)
    # so it lands exactly on the first scan cell.
    shot_w = 3840
    win_left, win_top, win_right, win_bottom = 1000, 200, 2750, 1365
    buf = _make_buffer(shot_w, win_bottom + 10)
    _plant_white_block(buf, shot_w, col=win_left + 12, row=win_top + 32 + 12)
    result = check_no_error_dialog(bytes(buf), shot_w,
                                   win_left, win_top, win_right, win_bottom)
    assert result == 1
