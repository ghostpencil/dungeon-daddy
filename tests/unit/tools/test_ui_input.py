import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

import pytest
from ui_input import app_to_screen


@pytest.mark.parametrize("scale,rect,app_xy,expected", [
    # 1.0× scale
    (1.0,  (0, 0, 1400, 932),     (0, 900),    (0, 32)),
    (1.0,  (0, 0, 1400, 932),     (700, 450),  (700, 482)),
    (1.0,  (0, 0, 1400, 932),     (1400, 0),   (1400, 932)),
    # 1.25× scale
    (1.25, (0, 0, 1750, 1165),    (0, 900),    (0, 40)),
    (1.25, (0, 0, 1750, 1165),    (700, 450),  (875, 603)),
    (1.25, (0, 0, 1750, 1165),    (1400, 0),   (1750, 1165)),
    # 1.25× scale with window offset
    (1.25, (100, 50, 1850, 1215), (700, 450),  (975, 653)),
])
def test_app_to_screen(scale, rect, app_xy, expected):
    with patch("dpi.scale", return_value=scale):
        assert app_to_screen(rect, *app_xy) == expected
