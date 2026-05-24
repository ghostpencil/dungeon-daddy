## Portable UI Smoke Tests

Make the smoke-test infrastructure resilient to DPI scaling, multi-monitor layouts,
and (eventually) non-Windows platforms.

---

### Background

The existing smoke tests in `tools/` use a mix of hard-coded pixel values and
Windows-only Win32 APIs. They pass reliably on the developer's machine but will
fail on any machine with a different DPI scale factor, a multi-monitor setup
where the primary monitor is not the one with the app, or a non-Windows OS.

This feature spec documents every issue found and the concrete fix for each one.
No new third-party libraries are introduced. All changes stay within `ctypes`,
`mss`, and the existing helper modules.

---

### Testing philosophy

All target failure conditions — 125% DPI, secondary monitor, non-Windows — are
absent from the development machine. Every test must therefore be structured to
verify correctness through one of three strategies:

1. **Pure math tests:** functions like `app_to_screen` and `pixel_rgb` take
   numeric inputs and return numeric outputs with no Win32 calls. Pass mock
   scale factors and assert exact expected values. No hardware needed.

2. **Synthetic pixel buffers:** build a `bytearray` of known BGRA data, plant a
   known color at a computed physical offset, and verify the helper returns that
   color. Lets you test DPI coordinate math end-to-end without a real screen.

3. **Mock injection:** patch `dpi.scale`, `sys.platform`, `ctypes.windll.*`, or
   `mss.MSS` to simulate conditions that cannot be replicated locally. Use
   `unittest.mock.patch` so the real implementation is never touched during
   the mock path.

At 100% DPI, integration tests against the live app provide a sanity check that
the refactored code still works under the only configuration that can be
observed directly.

---

### Issue 1 — Windows-only APIs (platform blocker)

**Root cause:** `ui_input.py` and `ui_harness.py` call `ctypes.windll.user32`
directly. Every function — `FindWindowW`, `GetWindowRect`, `SetWindowPos`,
`mouse_event`, `SendInput`, `PostMessageW` — is a Win32 API. The tests cannot
even be imported on macOS or Linux.

**Plan:**

1. Extract all Win32 calls into a new module `tools/platform_win32.py`.
   Give each function a clear, purpose-named wrapper (`find_window`,
   `get_window_rect`, `set_window_pos`, `send_click`, `send_key_combo`,
   `send_scroll`, `send_text`). Also move `get_dpi_scale()` here from its
   temporary location (see Issue 2 step 1 — it is created there first as a
   plain ctypes call, then migrated here).

2. Create a thin stub `tools/platform_stub.py` that provides the same
   interface but raises `NotImplementedError` with a clear message:
   _"UI smoke tests require Windows. Contribute a platform backend for your OS."_

3. Add a module `tools/platform_host.py` with a single public function
   `get_platform()` that returns the correct backend based on `sys.platform`.

4. Rewrite `ui_harness.py` and `ui_input.py` to import from `platform_host`
   instead of calling `ctypes.windll` directly.

**Acceptance criteria:**

- `import ui_harness` succeeds on macOS/Linux without raising `ImportError`.
- On non-Windows, attempting to launch a harness raises `NotImplementedError`
  with a clear message (not a cryptic `AttributeError`).
- Existing Windows behaviour is unchanged.

**Testing guidance:**

*Testing the stub path without macOS/Linux (mock `sys.platform`):*

```python
import importlib, sys
import pytest

def test_get_platform_returns_stub_on_non_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    import platform_host
    importlib.reload(platform_host)   # force re-evaluation of sys.platform check
    plat = platform_host.get_platform()
    with pytest.raises(NotImplementedError, match="Contribute"):
        plat.find_window("Dungeon Daddy")

def test_get_platform_returns_win32_on_windows():
    # Runs on the dev machine — verifies the real path is not broken
    import platform_host, platform_win32
    assert platform_host.get_platform() is platform_win32
```

*Verifying the import guard works:*
After the refactor, run `python -c "import ui_harness"` on Windows and confirm
it still completes without error. This is the only Windows-side check that can
be done directly; non-Windows import behaviour is covered by the monkeypatch
test above.

---

### Issue 2 — DPI scaling breaks pixel math

**Root cause:** Every pixel measurement in the test suite assumes 100% DPI
(96 DPI, scale factor 1.0). The hard-coded values are:

| Constant | Location | Assumed value | Breaks at |
|---|---|---|---|
| `OS_TITLEBAR_H = 32` | `smoke_helpers.py`, `ui_input.py` | 96 DPI | ≥ 125% |
| `WINDOW_W = 1400` used as physical pixel count | `smoke_helpers.py` | 96 DPI | ≥ 125% |
| `WINDOW_H = 900` used as physical pixel count | `smoke_helpers.py`, `ui_input.py` | 96 DPI | ≥ 125% |
| `_CHAR_W = 7` | `smoke_helpers.py` | 96 DPI | ≥ 125% |

When DPI is 125%, Windows physically renders each logical pixel as 1.25 physical
pixels. `mss` captures physical pixels (via `BitBlt` from the desktop DC), so
`WINDOW_W = 1400` logical pixels becomes 1750 physical pixels on screen. All
color-sampling regions and coordinate conversions then point to the wrong pixels.

**Prerequisite — DPI awareness mode of the test process**

The correctness of every coordinate calculation depends on `GetWindowRect`
returning physical pixel coordinates. `mss` always captures physical pixels;
`GetWindowRect` only returns physical coordinates when the calling process is
DPI-aware. Python 3.8+ sets a Per-Monitor DPI aware manifest by default, but
this must not be left as an implicit assumption.

Add an explicit DPI-awareness call to the very top of `ui_harness.py` (before
any window queries) so all Win32 geometry calls are in the same physical-pixel
space as `mss`:

```python
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
```

This call is idempotent and safe to make more than once. It must be made before
the first `FindWindowW` / `GetWindowRect` call; placing it at module level in
`ui_harness.py` guarantees this for all harness-based tests.

**Plan:**

1. Add a function `get_dpi_scale(hwnd: int = 0) -> float` directly in
   `ui_harness.py` (or a sibling `tools/dpi_win32.py`) using plain `ctypes`.
   This avoids a circular dependency with `platform_win32.py`, which does not
   exist yet at this stage of delivery. Implementation:
   ```python
   def get_dpi_scale(hwnd: int = 0) -> float:
       if hwnd:
           dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
       else:
           dpi = ctypes.windll.shcore.GetDpiForSystem()
       return dpi / 96.0
   ```
   When Issue 1 is implemented, migrate this function into `platform_win32.py`
   and update callers.

2. Add a helper `tools/dpi.py` that exposes `scale(hwnd: int = 0) -> float`.
   Do **not** cache the result: `GetDpiForWindow` is a cheap kernel call and
   caching is incorrect for windows that move between monitors with different
   DPI settings. On non-Windows it returns `1.0`.
   ```python
   import sys
   def scale(hwnd: int = 0) -> float:
       if sys.platform != "win32":
           return 1.0
       return get_dpi_scale(hwnd)
   ```

3. In `smoke_helpers.py`, define unscaled base constants and expose scaled
   versions computed via `dpi.scale()`. Keep the base values explicit so the
   origin of each number is clear and so callers can re-scale with a live hwnd:
   ```python
   from dpi import scale as _s
   _OS_TITLEBAR_H_BASE = 32   # logical pixels at 96 DPI
   _CHAR_W_BASE        = 7    # logical pixels at 96 DPI
   OS_TITLEBAR_H: int  = round(_OS_TITLEBAR_H_BASE * _s())
   _CHAR_W: float      = _CHAR_W_BASE * _s()
   ```
   `WINDOW_W` and `WINDOW_H` retain their logical-pixel meaning (1400, 900)
   and are used only for layout arithmetic. Physical pixel counts must come
   from the live `window_rect` (see Issue 5).

4. In `ui_input.py`, rewrite `app_to_screen` to scale **both axes** with
   `_s()`. The original formula only offsets by the titlebar height and does
   not scale the Arcade coordinate values, so x-direction clicks are wrong at
   any non-100% DPI:
   ```python
   from dpi import scale as _s

   _OS_TITLEBAR_H_BASE = 32
   _WINDOW_H_BASE      = 900

   def app_to_screen(window_rect, app_x, app_y):
       s = _s()
       win_left, win_top, _, _ = window_rect
       sx = win_left + round(app_x * s)
       sy = win_top + round(_OS_TITLEBAR_H_BASE * s) + round((_WINDOW_H_BASE - app_y) * s)
       return sx, sy
   ```
   Also update `pixel_rgb` and `scan_for_high_green` in `smoke_helpers.py` the
   same way — both use `int(arcade_x)` and `int(arcade_y)` without scaling,
   which produces the wrong physical pixel offset at non-100% DPI.

5. Audit every smoke test file for numeric literals passed as row/column
   arguments to `avg_color_region`, `pixel_rgb`, `scan_for_high_green`, or any
   click helper. Every such literal represents a logical pixel count and must be
   scaled. The rule is: **any argument that represents a distance or position
   in app/window space must be multiplied by `_s()` before use as a physical
   pixel index**. Literals used only as color-component thresholds (e.g.,
   `green_threshold=180`) are DPI-independent and must not be scaled.

   When auditing, pay special attention to `avg_color_region` call sites: both
   the `y_start`/`y_end` row arguments *and* the `x_start`/`x_end` column
   arguments are logical pixel offsets and each needs `round(value * _s())`.
   The default `x_end=None` inside `avg_color_region` (which falls back to
   `WINDOW_W`) is safe because `WINDOW_W` is now a logical-pixel constant; the
   caller must supply a scaled `x_end` whenever it means a physical boundary.

6. Add a calibration assertion at the start of each smoke test `run()` function.
   This converts the manual DPI printout into an automated guard that catches
   measurement errors immediately rather than producing silent wrong-pixel reads:
   ```python
   s = dpi.scale(hwnd)
   phys_w = h.window_rect[2] - h.window_rect[0]
   assert abs(phys_w - round(WINDOW_W * s)) < 10, (
       f"DPI mismatch: scale={s:.2f}, physical_w={phys_w}, expected≈{round(WINDOW_W * s)}"
   )
   ```

**Acceptance criteria:**

- `dpi.scale(hwnd)` returns the correct per-monitor scale factor (verified by
  the calibration assertion against the live window width at test start).
- Phase 3 and Phase 5 smoke tests pass on a machine set to 125% DPI.
- No bare numeric pixel literals remain in any smoke test except for values
  that are truly resolution/DPI-independent (e.g., color component thresholds).
- `app_to_screen` is verified by a unit test that passes a known `window_rect`
  and asserts the returned screen coordinates at both 1.0× and 1.25× scale.

**Testing guidance:**

*1. Verify `SetProcessDpiAwareness` succeeds (Windows-only, run once manually):*

```python
import ctypes
result = ctypes.windll.shcore.SetProcessDpiAwareness(2)
# S_OK = 0 (first call), E_ACCESSDENIED = 0x80070005 (already set by manifest)
# Both are acceptable. Any other value is a bug.
assert result in (0, 0x80070005), f"Unexpected HRESULT: {hex(result)}"
# Confirm the API pipeline works by reading the system DPI
# On a 100% DPI machine this must return 96
dpi = ctypes.windll.shcore.GetDpiForSystem()
assert dpi == 96, f"Unexpected system DPI {dpi} — check Windows display settings"
```

*2. `get_dpi_scale()` — mock the ctypes call to simulate 125% DPI:*

```python
from unittest.mock import patch

def test_get_dpi_scale_system_path():
    with patch("ctypes.windll.shcore.GetDpiForSystem", return_value=96):
        assert get_dpi_scale() == 1.0

def test_get_dpi_scale_125_percent():
    with patch("ctypes.windll.shcore.GetDpiForSystem", return_value=120):
        assert get_dpi_scale() == 1.25

def test_get_dpi_scale_hwnd_path():
    with patch("ctypes.windll.user32.GetDpiForWindow", return_value=144) as mock_fn:
        assert get_dpi_scale(hwnd=12345) == 1.5
        mock_fn.assert_called_once_with(12345)
```

*3. `app_to_screen` — pure math, no Win32, exact expected values:*

These values are derived from the formula
`sx = win_left + round(app_x * s)`,
`sy = win_top + round(32 * s) + round((900 - app_y) * s)`.

At scale 1.0, window at (0, 0, 1400, 932):

| Arcade (x, y) | Expected screen (sx, sy) | Notes |
|---|---|---|
| (0, 900) | (0, 32) | top-left of content area |
| (700, 450) | (700, 482) | centre: sy = 0 + 32 + 450 |
| (1400, 0) | (1400, 932) | bottom-right corner |
| (0, 0) | (0, 932) | bottom-left corner |

At scale 1.25, window at (0, 0, 1750, 1165):

| Arcade (x, y) | Expected screen (sx, sy) | Notes |
|---|---|---|
| (0, 900) | (0, 40) | sy = 0 + round(32×1.25) + 0 |
| (700, 450) | (875, 603) | sx = round(700×1.25); sy = 0+40+round(450×1.25) |
| (1400, 0) | (1750, 1165) | sx = round(1400×1.25); sy = 0+40+round(900×1.25) |

At scale 1.25, window offset at (100, 50, 1850, 1215):

| Arcade (x, y) | Expected screen (sx, sy) |
|---|---|
| (700, 450) | (975, 653) |

```python
from unittest.mock import patch

@pytest.mark.parametrize("scale,rect,app_xy,expected", [
    (1.0,  (0, 0, 1400, 932),   (0, 900),   (0, 32)),
    (1.0,  (0, 0, 1400, 932),   (700, 450), (700, 482)),
    (1.0,  (0, 0, 1400, 932),   (1400, 0),  (1400, 932)),
    (1.25, (0, 0, 1750, 1165),  (0, 900),   (0, 40)),
    (1.25, (0, 0, 1750, 1165),  (700, 450), (875, 603)),
    (1.25, (0, 0, 1750, 1165),  (1400, 0),  (1750, 1165)),
    (1.25, (100, 50, 1850, 1215), (700, 450), (975, 653)),
])
def test_app_to_screen(scale, rect, app_xy, expected):
    with patch("dpi.scale", return_value=scale):
        assert app_to_screen(rect, *app_xy) == expected
```

*4. `pixel_rgb` — synthetic BGRA buffer to confirm the coordinate formula:*

Plant a known color at the physical pixel corresponding to Arcade (100, 800)
at 1.25× scale, window at (0, 0). Using the formula:
- `px = round(100 × 1.25) = 125`
- `py = round(32 × 1.25) + round((900 − 800) × 1.25) = 40 + 125 = 165`
- `offset = (165 × shot_w + 125) × 4`

```python
from unittest.mock import patch

def test_pixel_rgb_at_125_scale():
    shot_w = 1750
    pixels = bytearray(200 * shot_w * 4)  # 200 rows, zero-filled
    # Plant (R=255, G=0, B=128) in BGRA byte order at physical (125, 165)
    offset = (165 * shot_w + 125) * 4
    pixels[offset]     = 128   # B
    pixels[offset + 1] = 0     # G
    pixels[offset + 2] = 255   # R
    pixels[offset + 3] = 255   # A

    with patch("smoke_helpers._s", return_value=1.25):
        r, g, b = pixel_rgb(bytes(pixels), shot_w, 0, 0, 100, 800)

    assert (r, g, b) == (255, 0, 128)
```

To confirm the OLD (unscaled) formula reads from the wrong pixel at 1.25×,
run the same test without the `patch` — `pixel_rgb` will return `(0, 0, 0)`
because it reads from offset `(165 * 1750 + 100) * 4` (missing the scaling on
`arcade_x`) which is zero-filled.

*5. Calibration assertion — test at 100% DPI with the live harness:*

At scale 1.0, the physical window width equals `WINDOW_W = 1400`. The assertion
tolerance is ±10px to allow for window chrome rounding. Run this as part of the
existing Phase 5 smoke test setup; if it trips, something in the DPI pipeline
is misconfigured before any pixel reads even start.

---

### Issue 3 — `mss.monitors[1]` misses multi-monitor windows

**Root cause:** `ui_harness.capture()` always grabs `sct.monitors[1]`, the
primary monitor. If the app window is on a secondary monitor (or if the
harness's `center_window()` did not yet move the window), the pixel buffer
will not contain the window.

**Plan:**

1. After `center_window()` (or `pin_window()`), call a new helper
   `_monitor_for_rect(rect, sct)` that iterates `sct.monitors[1:]` and
   returns the monitor dict whose bounding box has the greatest overlap with
   `window_rect`. Fall back to `sct.monitors[1]` if no overlap is found, and
   emit a warning so the failure is visible rather than silent.

   The overlap area between two rectangles is:
   ```
   ox = max(0, min(win_right, mon_right)  − max(win_left, mon_left))
   oy = max(0, min(win_bottom, mon_bottom) − max(win_top,  mon_top))
   overlap = ox * oy
   ```
   Return the monitor with the highest `overlap`; fall back to `monitors[1]` if
   all overlaps are zero.

2. Store the selected monitor dict as `self._monitor` on the harness instance.
   Update it whenever `refresh_window_rect()` is called. Because
   `_monitor_for_rect` requires an `mss` context (`sct`), `refresh_window_rect`
   must open a short-lived `mss.MSS()` context for this purpose:
   ```python
   def refresh_window_rect(self) -> None:
       rect = self._find_window_rect()
       if rect:
           self.window_rect = rect
           with mss.MSS() as sct:
               self._monitor = _monitor_for_rect(rect, sct)
   ```
   Opening an `mss.MSS()` context is cheap (no screenshot is taken); this does
   not meaningfully slow the harness.

3. In `capture()`, replace `sct.monitors[1]` with `self._monitor`.

4. `capture_window()` already captures only the window region and does not use
   `monitors[1]`, so it is unaffected.

**Note on `center_window`:** `center_window` uses `GetSystemMetrics(SM_CXSCREEN)`
to determine where to place the window. When the process is Per-Monitor DPI
aware (as set in Issue 2's prerequisite step), `GetSystemMetrics` returns
physical pixel dimensions for the primary monitor, which is the correct value
to use with `SetWindowPos`. No change is needed here, but this behaviour
depends on the DPI awareness mode being set correctly before the first Win32
call — another reason Issue 2's prerequisite step is non-negotiable.

**Acceptance criteria:**

- On a dual-monitor setup where the app is launched on the secondary monitor,
  `capture()` returns a screenshot that contains the app window.
- `_monitor_for_rect` is unit-tested with mock monitor dicts in
  `tests/unit/test_ui_harness_monitor.py`.

**Testing guidance:**

`_monitor_for_rect` is a pure function over dicts. All cases are testable with
synthetic monitor layouts — no second physical monitor is needed.

```python
# Synthetic two-monitor layout (side by side, 1920×1080 each)
_M_ALL = {"left": 0,    "top": 0, "width": 3840, "height": 1080}
_M1    = {"left": 0,    "top": 0, "width": 1920, "height": 1080}
_M2    = {"left": 1920, "top": 0, "width": 1920, "height": 1080}

class _FakeSct:
    monitors = [_M_ALL, _M1, _M2]

@pytest.mark.parametrize("rect,expected_mon", [
    # Window fully on monitor 1
    ((100,  50, 1500, 1000), _M1),
    # Window fully on monitor 2
    ((2000, 50, 3500, 1000), _M2),
    # Window straddling — 1820 px on M1, 80 px on M2 → M1 wins
    # overlap M1: 1820×950=1_729_000  overlap M2: 80×950=76_000
    ((100,  50, 2000, 1000), _M1),
    # Window straddling — 120 px on M1, 1580 px on M2 → M2 wins
    # overlap M1: 120×950=114_000  overlap M2: 1580×950=1_501_000
    ((1800, 50, 3500, 1000), _M2),
])
def test_monitor_for_rect_selection(rect, expected_mon):
    assert _monitor_for_rect(rect, _FakeSct()) is expected_mon

def test_monitor_for_rect_off_screen_falls_back_to_m1():
    # Window entirely off both monitors — must warn and fall back
    with pytest.warns(UserWarning, match="overlap"):
        result = _monitor_for_rect((5000, 50, 6400, 1000), _FakeSct())
    assert result is _M1

def test_monitor_for_rect_single_monitor():
    # Common case: only one physical monitor — always returns it
    class _Single:
        monitors = [_M_ALL, _M1]
    assert _monitor_for_rect((100, 50, 1400, 950), _Single()) is _M1
```

*Testing `refresh_window_rect` updates `self._monitor` (mock `mss`):*

```python
from unittest.mock import patch, MagicMock

def test_refresh_window_rect_updates_monitor():
    fake_monitor = {"left": 1920, "top": 0, "width": 1920, "height": 1080}

    with patch("ui_harness.mss.MSS") as mock_mss_cls, \
         patch("ui_harness._monitor_for_rect", return_value=fake_monitor) as mock_mfr, \
         patch("ui_harness.UITestHarness._find_window_rect",
               return_value=(1950, 50, 3350, 950)):

        mock_sct = MagicMock()
        mock_mss_cls.return_value.__enter__ = lambda s: mock_sct
        mock_mss_cls.return_value.__exit__  = MagicMock(return_value=False)

        h = UITestHarness.__new__(UITestHarness)
        h.window_rect = None
        h._monitor    = None
        h.refresh_window_rect()

        mock_mfr.assert_called_once_with((1950, 50, 3350, 950), mock_sct)
        assert h._monitor is fake_monitor
```

---

### Issue 4 — `_CHAR_W = 7` hard-codes font metric at 96 DPI

**Root cause:** `menu_slot_x()` and `menu_slot_center_x()` in `smoke_helpers.py`
estimate menu item positions by multiplying character count by `_CHAR_W = 7`.
That value was measured visually at 96 DPI. At higher DPI the rendered font is
physically wider, so the computed click target drifts off the actual label.

**Plan:**

This is resolved as part of Issue 2. Applying `_CHAR_W = _CHAR_W_BASE * _s()`
corrects the physical width at any DPI. No additional work is needed beyond the
DPI scaling pass in Issue 2.

However, the menu-slot helpers are inherently fragile (they depend on font
metrics, not widget geometry). Add a comment noting that these helpers are
approximate and that tests relying on them should prefer the MCP-based
`left_click` approach once the window is pinned, since MCP click coordinates
map directly to screen pixels and are DPI-stable.

**Testing guidance:**

The menu-slot calculations are pure arithmetic. Test them by mocking `_s()` and
asserting the returned coordinates scale proportionally.

`menu_slot_center_x("File")` at 96 DPI:
- slot_w = 4 chars × 7 + PAD_MD × 2 = 28 + 24 = 52
- center_x = PAD_MD + 52 / 2 = 12 + 26 = 38.0

At 1.25× the same formula with `_CHAR_W = 8.75` and `PAD_MD` unchanged:
- slot_w = 4 × 8.75 + 12 × 2 = 35 + 24 = 59
- center_x = 12 + 59 / 2 = 41.5

```python
def test_menu_slot_center_x_scales_with_dpi():
    with patch("smoke_helpers._s", return_value=1.0):
        import importlib, smoke_helpers
        importlib.reload(smoke_helpers)   # re-run module-level _CHAR_W assignment
        x_1x = smoke_helpers.menu_slot_center_x("File")

    with patch("smoke_helpers._s", return_value=1.25):
        importlib.reload(smoke_helpers)
        x_125x = smoke_helpers.menu_slot_center_x("File")

    assert x_125x > x_1x, "scaled centre must be wider than 1× centre"
    assert abs(x_125x - 41.5) < 0.1
    assert abs(x_1x  - 38.0) < 0.1
```

Note: `PAD_MD` (used as horizontal padding in slot width) is itself a logical
pixel value and may also need scaling for complete accuracy. If visual tests on
a 125% DPI machine show menu clicks still missing, add `PAD_MD` to the DPI
scaling pass.

---

### Issue 5 — Hard-coded `WINDOW_W` as physical scan boundary

**Root cause:** `check_no_error_dialog` computes its right scan boundary as
`win_left + WINDOW_W` (i.e., `win_left + 1400`). At 125% DPI, the physical
window is 1750px wide, so the right ~350px of the window is never scanned.
It also means the function would scan past the window's right edge at any DPI
below 100% (if such a configuration existed).

After this fix, the function's y-start calculation (`win_top + OS_TITLEBAR_H +
border`) still uses `OS_TITLEBAR_H` from `smoke_helpers.py`. Until Issue 2 is
implemented that constant is still the unscaled 32px value. Implement Issue 5
first (it is self-contained), then Issue 2 (which scales `OS_TITLEBAR_H`),
so the two fixes compose correctly without a separate follow-up.

**Plan:**

1. Change the function signature to accept `win_right: int` and `win_bottom: int`
   alongside `win_left` and `win_top` (all four are already available in every
   caller via `h.window_rect`).

2. Replace `win_left + WINDOW_W` with `win_right` and
   `win_top + OS_TITLEBAR_H + WINDOW_H` with `win_bottom`. Pass `win_bottom`
   directly; do not reconstruct it from `win_top + WINDOW_H` since `GetWindowRect`
   already provides the correct physical bottom coordinate.

3. Update every call site in the smoke test files to unpack and pass all four
   bounds from `h.window_rect`.

**Acceptance criteria:**

- `check_no_error_dialog` accepts and uses live window bounds.
- At 125% DPI, the function scans the full 1750×1125 physical window area.
- Existing unit tests for the helper are updated to pass the new arguments.

**Testing guidance:**

`check_no_error_dialog` is pure pixel math — no Win32 or `mss` calls. Build a
synthetic buffer that demonstrates the old boundary bug and confirm the fix
closes it. The key test: plant a bright-white block just beyond column 1400
(the old hard-coded limit) and verify the pre-fix call misses it while the
post-fix call catches it.

```python
def _make_buffer(shot_w: int, height: int) -> bytearray:
    """Zero-filled BGRA buffer (black = background, passes error check)."""
    return bytearray(height * shot_w * 4)

def _plant_white_block(buf: bytearray, shot_w: int,
                        col: int, row: int, size: int = 30) -> None:
    """Paint a size×size white block (R=G=B=255) at physical (col, row)."""
    for dr in range(size):
        for dc in range(size):
            offset = ((row + dr) * shot_w + (col + dc)) * 4
            buf[offset]     = 255  # B
            buf[offset + 1] = 255  # G
            buf[offset + 2] = 255  # R
            buf[offset + 3] = 255  # A

def test_check_no_error_dialog_detects_block_past_1400():
    """
    Old code: x_limit = win_left + WINDOW_W - border = 0 + 1400 - 12 = 1388
              loop: range(12, 1358, 30) → last col 1332, covers up to col 1361
    New code: x_limit = win_right - border = 1750 - 12 = 1738
              loop: range(12, 1708, 30) → includes col 1452 onward

    The block must be planted at a scan-grid position so it falls fully inside
    one 30×30 scan cell and its average exceeds the 200 threshold.
    Scan columns: x_start=12, step=30 → 12, 42, …, 1332 (old last), 1362, …, 1452, …
    Scan rows:    y_start = win_top + OS_TITLEBAR_H + border = 0 + 32 + 12 = 44, step=30

    col=1452, row=44 is the first scan cell past the old WINDOW_W=1400 boundary.
    Using off-grid coordinates (e.g. col=1450, row=60) causes the block to straddle
    multiple scan cells; the per-cell average drops below 200 and the block goes
    undetected even with the fix applied.
    """
    shot_w  = 1750
    win_left, win_top, win_right, win_bottom = 0, 0, 1750, 1165

    buf = _make_buffer(shot_w, win_bottom)
    # col=1452 is on the scan grid (12 + 30×48) and past the old 1400-col boundary.
    # row=44 is y_start — the first scan row — so the block is fully inside one cell.
    _plant_white_block(buf, shot_w, col=1452, row=44)

    # New signature: must detect the block
    result = check_no_error_dialog(bytes(buf), shot_w,
                                   win_left, win_top, win_right, win_bottom)
    assert result == 1, "Expected failure: bright block inside window not detected"

def test_check_no_error_dialog_clean_window_passes():
    shot_w = 1750
    win_left, win_top, win_right, win_bottom = 0, 0, 1750, 1165
    buf = _make_buffer(shot_w, win_bottom)
    result = check_no_error_dialog(bytes(buf), shot_w,
                                   win_left, win_top, win_right, win_bottom)
    assert result == 0

def test_check_no_error_dialog_nonzero_window_origin():
    """Verify bounds math is correct when the window is not at (0, 0).

    Block is planted at (x_start, y_start) = (win_left+border, win_top+OS_TITLEBAR_H+border)
    so it lands exactly on the first scan cell and is fully detected.
    Off-grid offsets like (win_left+50, win_top+60) straddle scan cells and
    produce averages below the threshold — use scan-aligned coordinates.
    """
    shot_w = 3840   # simulate a wide full-screen buffer
    win_left, win_top, win_right, win_bottom = 1000, 200, 2750, 1365
    buf = _make_buffer(shot_w, win_bottom + 10)
    # x_start = win_left + border = 1012; y_start = win_top + 32 + 12 = 244
    _plant_white_block(buf, shot_w, col=win_left + 12, row=win_top + 32 + 12)
    result = check_no_error_dialog(bytes(buf), shot_w,
                                   win_left, win_top, win_right, win_bottom)
    assert result == 1
```

---

### Delivery order

Implement in this order to keep each step independently testable and to avoid
circular module dependencies:

1. **Issue 5** — smallest, self-contained, no new modules. After this step,
   `check_no_error_dialog` uses live bounds, but `OS_TITLEBAR_H` in its
   y-start offset is still unscaled (fixed in the next step).

2. **Issue 2** — adds `dpi.py` and `get_dpi_scale()` (written directly in
   `ui_harness.py` or a sibling module using plain `ctypes`, **not** in
   `platform_win32.py` which does not exist yet). Scales all pixel math and
   adds the DPI-awareness prerequisite. Validates with the calibration
   assertion at test start.

3. **Issue 3** — adds `_monitor_for_rect` and unit tests. Depends on the DPI
   awareness mode being set (Issue 2 prerequisite), so comes after Issue 2.

4. **Issue 1** — platform abstraction layer; largest refactor, saved for last
   so earlier fixes are not tangled with module restructuring. At this point,
   migrate `get_dpi_scale()` from its temporary location into `platform_win32.py`
   and update `dpi.py` to call it via the platform abstraction.

5. **Issue 4** — resolved by Issue 2; only a comment addition remains.

---

### Out of scope

- macOS or Linux UI backend implementations (Issue 1 only adds the stub and
  the abstraction boundary; a real implementation requires OS-specific work
  outside this spec).
- Switching the smoke tests from pixel-color checks to accessibility-API or
  widget-ID checks. That is a larger architectural change and a separate
  decision.
- Automated CI on non-Windows runners. That depends on Issue 1's non-Windows
  backend existing first.
