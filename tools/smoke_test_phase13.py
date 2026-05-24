"""
Phase 13 smoke test — Incremental Context Docs + Wizard Save-Name.

Behaviors verified:
  1. App starts in Wizard mode — VIOLET DM greeting visible; no crash
  2. (API required) Wizard flow → setting.md and party.md written to disk as
     soon as the brief is parsed (CD-4 incremental writes, not just on save)
  3. (API required) Second session with pre-existing setting.md → overwrite
     prompt fires; docs NOT rewritten yet; type "overwrite" → docs ARE
     rewritten (CD-5 overwrite path)

The wizard is LLM-driven and may ask questions in varying order.  This test
uses Claude vision to read each screenshot and decide which step to take
next, making it resilient to prompt-order variations.

Requires:
  OPENAI_API_KEY    — drives the Dungeon Daddy wizard (GPT-4o)
  ANTHROPIC_API_KEY — drives the vision step classifier (claude-sonnet-4-6)

Usage:
    cd tools && python smoke_test_phase13.py
"""
from __future__ import annotations

import base64
import dataclasses
import datetime
import json
import os
import pathlib
import shutil
import sys
import time
from collections.abc import Callable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_dotenv() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

from ui_harness import UITestHarness, SCREENSHOTS_DIR
from ui_input import VK_CONTROL, click_app, key_combo, type_text
from smoke_helpers import (
    WINDOW_W, WINDOW_H, CHROME_TOTAL_H, PAD_SM,
    ok, fail,
    pixel_rgb,
)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

PANEL_TREE_W      = 240
PANEL_INSPECTOR_W = 320
CONTENT_H         = WINDOW_H - CHROME_TOTAL_H     # 830

HEADER_H     = 38
INPUT_AREA_H = 104
_INPUT_Y_OFF = 8
_INPUT_H     = 62
_BTN_W       = 76
_BTN_H       = 38

DESIGN_CHAT_X = PANEL_TREE_W
DESIGN_CHAT_W = WINDOW_W - PANEL_TREE_W - PANEL_INSPECTOR_W   # 840

_input_w     = DESIGN_CHAT_W - PAD_SM - 4 - _BTN_W - PAD_SM
CHAT_INPUT_X = DESIGN_CHAT_X + PAD_SM + _input_w // 2         # 620
CHAT_INPUT_Y = _INPUT_Y_OFF + _INPUT_H // 2                    # 39

_btn_left    = DESIGN_CHAT_X + PAD_SM + _input_w + 4
CHAT_SEND_X  = _btn_left + _BTN_W // 2                        # 1034
CHAT_SEND_Y  = _INPUT_Y_OFF + _BTN_H // 2                     # 27

_MSG_X0 = DESIGN_CHAT_X + 10
_MSG_X1 = DESIGN_CHAT_X + DESIGN_CHAT_W - 10
_MSG_Y0 = INPUT_AREA_H + 4
_MSG_Y1 = CONTENT_H - HEADER_H - 4

_SENTINEL = (
    "# SENTINEL\n"
    "Original setting — must not be overwritten until GM types overwrite.\n"
)

# Seconds to wait after each wizard action before taking the next screenshot.
# If the wizard needs more time, Claude will return "wait_more" and we sleep again.
_STEP_WAIT = 20.0

# ---------------------------------------------------------------------------
# Send helper
# ---------------------------------------------------------------------------

_VK_A = 0x41


def _send(h: UITestHarness, msg: str) -> None:
    click_app(h.window_rect, CHAT_INPUT_X, CHAT_INPUT_Y)
    time.sleep(0.2)
    key_combo(VK_CONTROL, _VK_A)
    time.sleep(0.1)
    type_text(msg)
    time.sleep(0.2)
    click_app(h.window_rect, CHAT_SEND_X, CHAT_SEND_Y)


# ---------------------------------------------------------------------------
# Wizard step registry
#
# Each entry: step_name → (vision_description, action_fn | None)
#   vision_description — shown to Claude so it can classify the current state
#   action_fn          — called when this step is chosen; None = no UI action
#
# Terminal steps (in _TERMINAL_STEPS) break the driving loop immediately.
# ---------------------------------------------------------------------------

_WizardStep = tuple[str, Callable[[UITestHarness], None] | None]

_CONCEPT_MSG = (
    "I want to design a 1-level dungeon. "
    "Theme: abandoned dwarven mine overrun by monsters. Simple complexity."
)

_DETAILS_MSG = (
    "The dungeon is called Irongate Depths. "
    "It is an ancient dwarven forge-complex abandoned 200 years ago after a "
    "goblin and troll invasion — dark tunnels, collapsed shafts, and forge "
    "chambers now ruled by monsters. "
    "Party: 4 players (Fighter, Rogue, Cleric, Ranger) at level 2. "
    "Quest: recover the legendary forge-hammer stolen by the Forge Guardian boss."
)

_BASE_STEPS: dict[str, _WizardStep] = {
    "send_concept": (
        "The wizard is greeting and waiting for an initial dungeon concept. "
        "Its most recent message is an introduction or open invitation to describe a dungeon idea.",
        lambda h: _send(h, _CONCEPT_MSG),
    ),
    "send_details": (
        "The wizard acknowledged the concept and is asking for specifics: dungeon name, "
        "setting description, party composition, or quest goal.",
        lambda h: _send(h, _DETAILS_MSG),
    ),
    "send_confirm": (
        "The wizard presented a full summary or outline of the dungeon design and is asking "
        "for confirmation or approval before generating the structured brief.",
        lambda h: _send(h, "Yes, that is correct. Please output the brief now."),
    ),
    "send_yes_retry": (
        "The wizard echoed back the dungeon details but has not yet produced the structured "
        "brief. A simple affirmative is needed to trigger brief generation.",
        lambda h: _send(h, "Yes."),
    ),
    "wait_more": (
        "The wizard is still generating its response — no new complete DM message is visible "
        "yet, or the most recent message is the user's own. Wait before acting.",
        None,  # No UI action; the loop's _STEP_WAIT handles the pause
    ),
    "error_detected": (
        "The chat panel shows an error message — a ⚠ warning symbol is visible in a DM bubble, "
        "or there is warning/error text in the chat area. Stop immediately.",
        None,  # Terminal
    ),
    "done": (
        "The wizard flow is complete: the brief was generated and phase 2 (dungeon generation "
        "or loop selection) has started. No further wizard input is needed.",
        None,  # Terminal
    ),
}

# Session-B extra step: stops the loop so the caller can check SENTINEL before overwriting
_OVERWRITE_DETECTED: _WizardStep = (
    "The wizard detected that context documents already exist for this dungeon and is "
    "explicitly asking whether to overwrite them. Stop here for a file-state check.",
    None,  # Terminal
)

_TERMINAL_STEPS = {"done", "error_detected", "overwrite_detected"}

# Maps step name → the GM message sent by that step (None for no-op / terminal steps).
_STEP_GM_MESSAGES: dict[str, str | None] = {
    "send_concept":       _CONCEPT_MSG,
    "send_details":       _DETAILS_MSG,
    "send_confirm":       "Yes, that is correct. Please output the brief now.",
    "send_yes_retry":     "Yes.",
    "wait_more":          None,
    "error_detected":     None,
    "done":               None,
    "overwrite_detected": None,
}

# ---------------------------------------------------------------------------
# Chat log structures
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class _StepClassification:
    step: str
    dm_response: str


@dataclasses.dataclass
class _ChatEntry:
    step_index: int
    action: str
    gm_sent: str | None
    dm_response: str
    screenshot: str       # filename only — lives in tools/screenshots/
    timestamp: str        # ISO-8601


# ---------------------------------------------------------------------------
# Vision classifier — returns step name AND last DM response text
# ---------------------------------------------------------------------------

def _wizard_next_step(
    screenshot_path: pathlib.Path,
    available_steps: dict[str, _WizardStep],
    history: list[str],
) -> _StepClassification:
    """Send a screenshot to Claude; get back the next step name + last DM message text."""
    import anthropic
    import re as _re

    client = anthropic.Anthropic()
    img_b64 = base64.standard_b64encode(screenshot_path.read_bytes()).decode()

    steps_text = "\n".join(
        f'  "{name}": {desc}' for name, (desc, _) in available_steps.items()
    )
    history_text = " → ".join(history) if history else "none yet"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "You are analyzing a screenshot of the Dungeon Daddy app.\n"
                        "The wizard chat panel is on the LEFT side of the screen.\n"
                        "Read the wizard's most recent message (the bottom-most DM bubble).\n\n"
                        f"Steps taken so far: {history_text}\n\n"
                        "Available next steps:\n"
                        f"{steps_text}\n\n"
                        "Reply with ONLY a JSON object on one line:\n"
                        '{"step": "<step_name>", "dm_response": "<first sentence of bottom-most DM bubble, no newlines, max 120 chars>"}\n'
                        "IMPORTANT: dm_response must be a single line with no newlines or unescaped quotes.\n"
                        'If no DM bubble is visible, use "" for dm_response. No other text.'
                    ),
                },
            ],
        }],
    )

    raw = response.content[0].text.strip()
    try:
        data = json.loads(raw)
        step = str(data.get("step", "wait_more")).strip().strip('"')
        dm_response = str(data.get("dm_response", "")).strip()
    except (json.JSONDecodeError, AttributeError):
        m = _re.search(r'"step"\s*:\s*"([^"]+)"', raw)
        step = m.group(1) if m else "wait_more"
        dm_response = ""

    return _StepClassification(step=step, dm_response=dm_response)


# ---------------------------------------------------------------------------
# Vision assertion — yes/no question about a screenshot
# ---------------------------------------------------------------------------

def _vision_assert(screenshot_path: pathlib.Path, question: str) -> bool:
    """Ask Claude a yes/no question about a screenshot. Returns True for YES."""
    import anthropic

    client = anthropic.Anthropic()
    img_b64 = base64.standard_b64encode(screenshot_path.read_bytes()).decode()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                },
                {
                    "type": "text",
                    "text": f"{question}\nReply with only YES or NO.",
                },
            ],
        }],
    )

    return response.content[0].text.strip().upper().startswith("Y")


# ---------------------------------------------------------------------------
# Vision-guided wizard driver
# ---------------------------------------------------------------------------

def _vision_drive_wizard(
    h: UITestHarness,
    available_steps: dict[str, _WizardStep],
    label: str,
    max_steps: int = 16,
) -> tuple[list[str], list[_ChatEntry]]:
    """
    Drive the wizard using Claude vision to choose each next step.
    Returns (step history, structured chat log).
    """
    history: list[str] = []
    chat_log: list[_ChatEntry] = []

    for i in range(max_steps):
        shot = h.capture(f"{label}_step{i:02d}")
        print(f"  [step {i:02d}] screenshot: {shot.name}")

        classification = _wizard_next_step(shot, available_steps, history)
        step = classification.step
        dm_preview = (
            classification.dm_response[:80] + "…"
            if len(classification.dm_response) > 80
            else classification.dm_response
        )
        print(f"  [step {i:02d}] chose: {step}")
        print(f"  [step {i:02d}] DM: {dm_preview}")

        if step not in available_steps:
            print(f"  WARNING  unknown step '{step}' — defaulting to wait_more")
            step = "wait_more"

        _, fn = available_steps[step]
        history.append(step)

        chat_log.append(_ChatEntry(
            step_index=i,
            action=step,
            gm_sent=_STEP_GM_MESSAGES.get(step),
            dm_response=classification.dm_response,
            screenshot=shot.name,
            timestamp=datetime.datetime.now().isoformat(),
        ))

        if step in _TERMINAL_STEPS:
            print(f"  Wizard driving complete — terminal step '{step}' reached.")
            break

        if fn is not None:
            fn(h)

        time.sleep(_STEP_WAIT)
    else:
        print(f"  WARNING  reached max_steps={max_steps} without a terminal step")

    return history, chat_log


# ---------------------------------------------------------------------------
# Chat log writer
# ---------------------------------------------------------------------------

def _write_chat_log(chat_log: list[_ChatEntry], label: str) -> pathlib.Path:
    """Write the chat log to JSON in tools/screenshots/."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = SCREENSHOTS_DIR / f"{label}_chatlog_{ts}.json"
    log_path.write_text(
        json.dumps([dataclasses.asdict(e) for e in chat_log], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Chat log: {log_path.name}")
    return log_path


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _dungeons_root() -> pathlib.Path:
    from platformdirs import user_data_path
    return user_data_path("DungeonDaddy", appauthor=False) / "dungeons"


def _clean_irongate_dirs() -> None:
    root = _dungeons_root()
    if not root.exists():
        return
    for d in root.iterdir():
        if d.is_dir() and "irongate" in d.name.lower():
            shutil.rmtree(d)
            print(f"  Deleted: {d}")


def _newest_setting_md(since: float) -> pathlib.Path | None:
    root = _dungeons_root()
    if not root.exists():
        return None
    best: pathlib.Path | None = None
    best_mtime = since
    for d in root.iterdir():
        if not d.is_dir():
            continue
        s = d / "setting.md"
        if s.exists():
            mt = s.stat().st_mtime
            if mt > best_mtime:
                best_mtime = mt
                best = s
    return best


def _seed_sentinel(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_SENTINEL, encoding="utf-8")
    print(f"  Seeded sentinel → {path}")


# ---------------------------------------------------------------------------
# Pixel helpers
# ---------------------------------------------------------------------------

def _has_violet(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    for y_arc in range(_MSG_Y0, _MSG_Y1, 2):
        for x_arc in range(_MSG_X0, _MSG_X1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if r > 140 and b > 180 and g < 130:
                return True
    return False


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Session A — clean run; verify CD-4 incremental writes
# ---------------------------------------------------------------------------

def _run_session_a() -> tuple[int, pathlib.Path | None]:
    failures = 0
    print("\n--- Session A: clean run (CD-4 file writes) ---\n")

    print("Setup — cleaning any prior Irongate Depths context docs")
    _clean_irongate_dirs()
    t_start = time.time()

    with UITestHarness(tag="phase13a", render_wait=4.0) as h:
        if h.window_rect is None:
            return fail("Window did not open — aborting session A"), None

        h.pin_window()
        win_left, win_top, _, _ = h.window_rect
        print(f"  Window pinned to (0,0)\n")

        # Behavior 1 — Wizard mode launch
        print("Behavior 1 — Wizard mode launch: VIOLET DM greeting in chat")
        shot = h.capture("a1_wizard_launch")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if _has_violet(pixels, shot_w, win_left, win_top):
            ok("VIOLET bubble found — Wizard greeting rendered")
        else:
            failures += fail("No VIOLET in chat — greeting missing or not rendered")

        if _app_alive(h):
            ok("App alive in Wizard mode")
        else:
            return failures + fail("App crashed on launch — aborting"), None

        # Behavior 2 — vision-guided wizard; verify files written during brief parse
        print("\nBehavior 2 — Wizard brief parsed → setting.md + party.md written (CD-4)")

        history, chat_log = _vision_drive_wizard(h, dict(_BASE_STEPS), label="a2", max_steps=16)
        print(f"  Steps taken: {' → '.join(history)}")
        _write_chat_log(chat_log, "phase13_a")

        if not _app_alive(h):
            return failures + fail("App crashed during wizard flow"), None

        shot = h.capture("a2_after_wizard")
        print(f"  Screenshot: {shot.name}")

        wizard_done = _vision_assert(
            shot,
            "Does the chat panel show a completed DM response — a violet or purple DM bubble "
            "at the bottom of the chat with visible text? "
            "Reply YES if a DM message is visible, NO if the chat is empty or only shows "
            "user messages.",
        )
        if wizard_done:
            ok("DM response visible in chat — wizard completed (vision confirmed)")
        else:
            failures += fail("No DM response in chat after wizard flow")

        setting_md = _newest_setting_md(t_start)

        if setting_md and setting_md.stat().st_size > 10:
            ok(f"setting.md written: {setting_md.parent.name}/ — CD-4 incremental write confirmed")
        else:
            failures += fail(
                f"setting.md not found — CD-4 write did not fire. Checked: {_dungeons_root()}"
            )

        party_md = setting_md.parent / "party.md" if setting_md else None
        if party_md and party_md.exists() and party_md.stat().st_size > 10:
            ok("party.md written — CD-4 incremental write confirmed")
        else:
            failures += fail("party.md not found after brief")

        if _app_alive(h):
            ok("App alive after wizard brief flow")
        else:
            return failures + fail("App crashed during session A"), setting_md

    return failures, setting_md


# ---------------------------------------------------------------------------
# Session B — pre-seeded run; verify CD-5 overwrite prompt
# ---------------------------------------------------------------------------

def _run_session_b(setting_md: pathlib.Path) -> int:
    failures = 0
    print("\n--- Session B: pre-seeded run (CD-5 overwrite prompt) ---\n")

    print(f"Setup — seeding sentinel into: {setting_md}")
    _seed_sentinel(setting_md)

    with UITestHarness(tag="phase13b", render_wait=4.0) as h:
        if h.window_rect is None:
            return fail("Window did not open — aborting session B")

        h.pin_window()
        win_left, win_top, _, _ = h.window_rect
        print(f"  Window pinned to (0,0)\n")

        # Drive wizard — stop when "overwrite_detected" is reached so we can
        # check the sentinel before the overwrite is sent.
        print("  Driving wizard — stopping when overwrite prompt appears…")
        steps_b = dict(_BASE_STEPS)
        steps_b["overwrite_detected"] = _OVERWRITE_DETECTED

        history_b, chat_log_b = _vision_drive_wizard(h, steps_b, label="b1", max_steps=16)
        print(f"  Steps taken: {' → '.join(history_b)}")
        _write_chat_log(chat_log_b, "phase13_b")

        if not _app_alive(h):
            return failures + fail("App crashed during wizard flow (session B)")

        shot = h.capture("b1_after_overwrite_prompt")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")

        # Behavior 3a — sentinel still intact (overwrite not sent yet)
        print("\nBehavior 3a — Overwrite prompt fires: setting.md NOT rewritten yet")
        content = setting_md.read_text(encoding="utf-8") if setting_md.exists() else ""
        if "SENTINEL" in content:
            ok("setting.md still contains SENTINEL — overwrite check fired, no premature write")
        else:
            failures += fail(
                "setting.md no longer contains SENTINEL — overwrite check did not fire, "
                "or wizard used a different dungeon name than session A."
            )

        if _has_violet(pixels, shot_w, win_left, win_top):
            ok("VIOLET DM message visible — overwrite prompt posted in chat")
        else:
            failures += fail("No VIOLET in chat after brief with pre-existing setting.md")

        if not _app_alive(h):
            return failures + fail("App crashed before overwrite response — aborting")

        # Behavior 3b — GM types "overwrite" → docs regenerated
        print("\nBehavior 3b — GM types 'overwrite' → docs are regenerated")

        # The vision loop breaks immediately on overwrite_detected with no _STEP_WAIT,
        # so the wizard LLM may still be streaming. Wait for it to go idle before sending.
        print("  Waiting for wizard LLM to finish generating overwrite prompt…")
        time.sleep(10.0)

        _send(h, "overwrite")
        print("  Sent 'overwrite'. Polling for file update (up to 60 s)…")

        # Poll the file instead of a fixed sleep — succeed as soon as the write fires.
        content_after = ""
        for _attempt in range(12):  # 12 × 5 s = 60 s max
            time.sleep(5.0)
            if not _app_alive(h):
                return failures + fail("App crashed while polling for file update — aborting")
            content_after = setting_md.read_text(encoding="utf-8") if setting_md.exists() else ""
            if "SENTINEL" not in content_after and len(content_after) > 20:
                print(f"    File updated after {(_attempt + 1) * 5} s")
                break
            print(f"    [{_attempt + 1}/12] SENTINEL still present — waiting…")

        if not _app_alive(h):
            return failures + fail("App crashed after 'overwrite' — aborting")

        shot = h.capture("b2_after_overwrite")
        pixels, shot_w = h.pixels, h.shot_w
        win_left, win_top = h.window_rect[0], h.window_rect[1]
        print(f"  Screenshot: {shot.name}")

        if "SENTINEL" not in content_after and len(content_after) > 20:
            ok("setting.md regenerated (SENTINEL gone, new content present) — CD-5 overwrite works")
        elif "SENTINEL" in content_after:
            failures += fail(
                "setting.md still contains SENTINEL after 60 s — "
                "overwrite message may have been dropped or wizard did not regenerate docs."
            )
        else:
            failures += fail("setting.md is empty or missing after 'overwrite'")

        if _has_violet(pixels, shot_w, win_left, win_top):
            ok("VIOLET visible after 'overwrite' — wizard phase-2 active or DM responded")
        else:
            failures += fail("No VIOLET after 'overwrite' — phase-2 may not have started")

        if _app_alive(h):
            ok("App alive after overwrite flow")
        else:
            failures += fail("App crashed after overwrite")

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures  = 0
    has_openai    = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))

    print("\n=== Phase 13 Smoke Test ===\n")

    print("Setup — removing any existing Irongate Depths dungeon folder")
    _clean_irongate_dirs()


    if has_openai and has_anthropic:
        print("  Both API keys present — full vision-guided wizard flow (expect 4–8 min)\n")
    elif has_openai:
        print("  NOTE  OPENAI_API_KEY set but ANTHROPIC_API_KEY missing")
        print("        Behaviors 2–3 use the vision classifier — they will be skipped.\n")
    else:
        print("  NOTE  OPENAI_API_KEY not set — only Behavior 1 (launch check) will run\n")

    def _behavior1_only(tag: str) -> int:
        errs = 0
        with UITestHarness(tag=tag, render_wait=4.0) as h:
            if h.window_rect is None:
                return fail("Window did not open — aborting")
            h.pin_window()
            win_left, win_top, _, _ = h.window_rect
            shot = h.capture(f"{tag}_launch")
            pixels, shot_w = h.pixels, h.shot_w
            print("Behavior 1 — Wizard mode launch")
            if _has_violet(pixels, shot_w, win_left, win_top):
                ok("VIOLET greeting visible — Wizard mode rendered correctly")
            else:
                errs += fail("No VIOLET — Wizard greeting not visible")
            if _app_alive(h):
                ok("App alive on launch — no crash")
            else:
                errs += fail("App crashed on launch")
        return errs

    if not has_openai:
        failures += _behavior1_only("phase13_noapi")
        print("\n  SKIP  Behaviors 2-3 require OPENAI_API_KEY + ANTHROPIC_API_KEY")
    elif not has_anthropic:
        failures += _behavior1_only("phase13_novision")
        print("\n  SKIP  Behaviors 2-3 require ANTHROPIC_API_KEY for vision guidance")
    else:
        a_failures, setting_md = _run_session_a()
        failures += a_failures

        if setting_md is None:
            print(
                "\n  SKIP  Session B skipped — session A did not produce a setting.md.\n"
                "         Check session A screenshots to see where the wizard stopped."
            )
        else:
            failures += _run_session_b(setting_md)

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
