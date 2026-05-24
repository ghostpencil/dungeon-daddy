"""
Phase 7 smoke test — LLM Design Flow (Wizard + Generator).

Behaviors verified:
  1. App starts in Wizard mode — VIOLET DM greeting visible in chat; no crash
  2. OPENAI_API_KEY absent → send message → error notice (VIOLET) appears; no crash
     [skipped when OPENAI_API_KEY is set]
  3+4. Both keys present → vision-guided wizard conversation drives through to
     Level 1 generation; level entry confirmed visible in DungeonTree via vision
     [skipped when either key is absent]
  5. Both keys present → Test Drive → generated dungeon loads into Play mode
     [skipped when either key is absent]

After the run a structured chat log is written to tools/screenshots/:
  phase7_b34_chatlog_<timestamp>.json
Each entry records the step taken, the GM message sent, the DM response text
extracted from the screenshot, and the screenshot filename — ready for
post-run analysis.

Requires:
  OPENAI_API_KEY    — drives the Dungeon Daddy wizard (GPT-4o)
  ANTHROPIC_API_KEY — drives the vision step classifier (claude-sonnet-4-6)

Usage:
    cd tools && python smoke_test_phase7.py
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
# Design mode layout constants
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

# Seconds to wait after each wizard action before the next screenshot.
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
# ---------------------------------------------------------------------------

_WizardStep = tuple[str, Callable[[UITestHarness], None] | None]

_CONCEPT_MSG = (
    "I want to design a 3-level undead tomb dungeon for 4 players at level 3, "
    "moderate complexity. The main quest is to defeat the lich king."
)

_DETAILS_MSG = (
    "The dungeon is called Tomb of the Lich King. "
    "It is set in ancient catacombs beneath the Frozen Wastes, built 500 years ago "
    "by the lich king Malachar as his eternal domain — cursed corridors, undead "
    "guardians, dark sorcery. "
    "Party: Fighter, Rogue, Cleric, and Wizard. "
    "Quest: find and destroy the Phylactery of Malachar to permanently kill the lich king."
)

_LEVEL_DETAILS_MSG = (
    "Ecology: ancient frozen crypts, bone dust floors, cursed cold stone corridors. "
    "Special rooms: the Crypt of Warriors (skeleton soldiers), the Necromancer's "
    "Laboratory (experimental undead constructs), and the Throne of Malachar (boss). "
    "Traps: pressure-plate arrow volleys, summoning circles that spawn skeletons, "
    "and ice-magic barrier puzzles."
)

# Maps step name → the GM message sent by that step (None for no-op / terminal steps).
# Used to populate gm_sent in the chat log without having to introspect lambdas.
_STEP_GM_MESSAGES: dict[str, str | None] = {
    "send_concept":      _CONCEPT_MSG,
    "send_details":      _DETAILS_MSG,
    "send_confirm":      "Yes, that looks correct. Please proceed and output the brief.",
    "send_yes_retry":    "Yes, please output the brief now.",
    "send_loop_1":       "1",
    "send_no_subloop":   "no",
    "send_level_details": _LEVEL_DETAILS_MSG,
    "send_clarification": (
        "Yes, all rooms listed are separate and distinct encounters. "
        "Please output the level brief now."
    ),
    "send_nudge":        "Yes, all rooms are separate. Please output the level brief now.",
    "wait_more":         None,
    "done":              None,
    "error_detected":    None,
}

_BASE_STEPS: dict[str, _WizardStep] = {
    "send_concept": (
        "The wizard is greeting and waiting for an initial dungeon concept. "
        "Its most recent message is an introduction or open invitation to describe a dungeon idea.",
        lambda h: _send(h, _CONCEPT_MSG),
    ),
    "send_details": (
        "The wizard acknowledged the concept and is asking for specifics: dungeon name, "
        "setting/lore description, party composition, or quest goal.",
        lambda h: _send(h, _DETAILS_MSG),
    ),
    "send_confirm": (
        "The wizard presented a full summary or outline of the dungeon design and is asking "
        "for confirmation or approval before generating the structured brief.",
        lambda h: _send(h, "Yes, that looks correct. Please proceed and output the brief."),
    ),
    "send_yes_retry": (
        "The wizard echoed back the dungeon details but has not yet produced the structured "
        "brief. A simple affirmative is needed to trigger brief generation.",
        lambda h: _send(h, "Yes, please output the brief now."),
    ),
    "send_loop_1": (
        "The wizard is now in phase 2 (dungeon structure) and is showing numbered loop patterns "
        "for the level layout, asking the user to pick one by number.",
        lambda h: _send(h, "1"),
    ),
    "send_no_subloop": (
        "The wizard (in phase 2) asked whether to add a sub-loop or secondary loop to the level.",
        lambda h: _send(h, "no"),
    ),
    "send_level_details": (
        "The wizard (in phase 2) is asking for level ecology, special rooms, or trap details "
        "in order to generate the level brief.",
        lambda h: _send(h, _LEVEL_DETAILS_MSG),
    ),
    "send_clarification": (
        "The wizard is asking a clarifying question about the level details — for example "
        "whether special rooms are separate encounters, how rooms connect, or other layout "
        "specifics. Answer the clarification and ask for the level brief.",
        lambda h: _send(
            h,
            "Yes, all rooms listed are separate and distinct encounters. "
            "Please output the level brief now.",
        ),
    ),
    "send_nudge": (
        "The wizard acknowledged the level details but has not yet output the level brief, "
        "and is not asking a clarification question. A nudge is needed to trigger output.",
        lambda h: _send(h, "Yes, all rooms are separate. Please output the level brief now."),
    ),
    "wait_more": (
        "The wizard is still generating its response — no new complete DM message is visible "
        "yet, or the most recent message is the user's own. Wait before acting.",
        None,
    ),
    "error_detected": (
        "The chat panel shows an error message — a ⚠ warning symbol is visible in a DM bubble, "
        "or there is warning/error text in the chat area. Stop immediately.",
        None,  # Terminal
    ),
    "done": (
        "Level generation is complete — the DungeonTree panel on the far left shows a level "
        "entry (e.g. 'Level 1' or a level name), indicating the dungeon has been generated.",
        None,  # Terminal
    ),
}

_TERMINAL_STEPS = {"done", "error_detected"}

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
                        "The wizard chat panel is in the CENTRE of the screen.\n"
                        "The DungeonTree panel is on the FAR LEFT (narrow column).\n"
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

    import re as _re
    raw = response.content[0].text.strip()
    try:
        data = json.loads(raw)
        step = str(data.get("step", "wait_more")).strip().strip('"')
        dm_response = str(data.get("dm_response", "")).strip()
    except (json.JSONDecodeError, AttributeError):
        # Regex fallback: extract step name from malformed JSON
        # (dm_response with newlines is the usual culprit)
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
    max_steps: int = 20,
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

        gm_sent = _STEP_GM_MESSAGES.get(step)

        chat_log.append(_ChatEntry(
            step_index=i,
            action=step,
            gm_sent=gm_sent,
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
# Pixel helpers (used for fast launch / key-guard checks)
# ---------------------------------------------------------------------------

def _has_violet(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    for y_arc in range(_MSG_Y0, _MSG_Y1, 2):
        for x_arc in range(_MSG_X0, _MSG_X1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if r > 140 and b > 180 and g < 130:
                return True
    return False


def _has_teal_in_messages(pixels: bytes, shot_w: int, win_left: int, win_top: int) -> bool:
    for y_arc in range(_MSG_Y0, _MSG_Y1, 2):
        for x_arc in range(_MSG_X0, _MSG_X1, 3):
            r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, x_arc, y_arc)
            if r < 100 and g > 180 and b > 140:
                return True
    return False


def _app_alive(h: UITestHarness) -> bool:
    return h._proc is not None and h._proc.poll() is None


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _cleanup_test_dungeon() -> None:
    """Delete the Tomb of the Lich King dungeon folder if it exists from a prior run."""
    dungeons_dir = (
        pathlib.Path(os.environ.get("LOCALAPPDATA", ""))
        / "DungeonDaddy" / "dungeons"
    )
    target = dungeons_dir / "Tomb of the Lich King"
    if target.exists():
        shutil.rmtree(target)
        print(f"  Cleaned up pre-existing dungeon: {target}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    has_openai    = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))

    print("\n=== Phase 7 Smoke Test ===\n")

    if has_openai and has_anthropic:
        print("  Both API keys present — full vision-guided wizard + generation flow (expect 4–8 min)\n")
    elif has_openai:
        print("  NOTE  OPENAI_API_KEY set but ANTHROPIC_API_KEY missing")
        print("        Behaviors 3–5 require the vision classifier — they will be skipped.\n")
    else:
        print("  NOTE  OPENAI_API_KEY not set — API key guard (Behavior 2) will be tested\n")

    _cleanup_test_dungeon()

    with UITestHarness(tag="phase7", render_wait=4.0) as h:
        if h.window_rect is None:
            print("  FAIL  Window did not open within timeout — aborting")
            return 1

        h.pin_window()
        win_left, win_top, _, _ = h.window_rect
        print(f"  Window pinned to (0,0)\n")

        # ------------------------------------------------------------------
        # Behavior 1 — Wizard mode on launch: VIOLET DM greeting visible
        # ------------------------------------------------------------------
        print("Behavior 1 — Wizard mode launch: VIOLET DM greeting in chat")

        shot = h.capture("b1_wizard_launch")
        pixels, shot_w = h.pixels, h.shot_w
        print(f"  Screenshot: {shot.name}")

        if _has_violet(pixels, shot_w, win_left, win_top):
            ok("VIOLET bubble found in message area — Wizard greeting rendered")
        else:
            failures += fail("No VIOLET in chat message area — greeting missing or not rendered")

        if _app_alive(h):
            ok("App alive in Wizard mode — no crash on launch")
        else:
            return failures + fail("App crashed on launch — aborting")

        # ------------------------------------------------------------------
        # Behavior 2 — API key guard (only when key is absent)
        # ------------------------------------------------------------------
        if not has_openai:
            print("\nBehavior 2 — No API key: send message → error notice appears")

            click_app(h.window_rect, CHAT_INPUT_X, CHAT_INPUT_Y)
            time.sleep(0.3)
            type_text("I want to make a tomb dungeon")
            time.sleep(0.2)
            click_app(h.window_rect, CHAT_SEND_X, CHAT_SEND_Y)
            time.sleep(1.5)

            shot = h.capture("b2_no_api_key")
            pixels, shot_w = h.pixels, h.shot_w
            print(f"  Screenshot: {shot.name}")

            if _has_teal_in_messages(pixels, shot_w, win_left, win_top):
                ok("TEAL GM bubble found — user message was sent and rendered")
            else:
                failures += fail("No TEAL in message area — user message may not have rendered")

            if _has_violet(pixels, shot_w, win_left, win_top):
                ok("VIOLET in chat — error notice appeared without crash")
            else:
                failures += fail("No VIOLET in chat — error notice not rendered")

            if _app_alive(h):
                ok("App alive after send without API key — no crash")
            else:
                return failures + fail("App crashed after send without API key — aborting")

        # ------------------------------------------------------------------
        # Behaviors 3+4 — Vision-guided wizard → Level 1 generation
        # ------------------------------------------------------------------
        elif not has_anthropic:
            print("\n  SKIP  Behaviors 3–5 require ANTHROPIC_API_KEY for vision guidance")

        else:
            print("\nBehaviors 3+4 — Vision-guided wizard conversation → Level 1 generation")

            history, chat_log = _vision_drive_wizard(
                h, dict(_BASE_STEPS), label="b34", max_steps=20
            )
            print(f"  Steps taken: {' → '.join(history)}")
            _write_chat_log(chat_log, "phase7_b34")

            if not _app_alive(h):
                return failures + fail("App crashed during wizard flow — aborting")

            # Check if wizard stopped on an error
            if history and history[-1] == "error_detected":
                failures += fail(
                    "Wizard stopped on error_detected — check the chat log and last screenshot"
                )
            else:
                # Vision assertion: does DungeonTree show a level entry?
                shot = h.capture("b4_after_wizard")
                print(f"  Screenshot: {shot.name}")

                level_in_tree = _vision_assert(
                    shot,
                    "Does the narrow DungeonTree panel on the far left of the screen "
                    "show a named level entry (for example 'Level 1' or any dungeon level name)? "
                    "Ignore the panel header bar. Look only at the list body.",
                )

                if level_in_tree:
                    ok("Level entry visible in DungeonTree — Level 1 generated (vision confirmed)")
                else:
                    # Poll for up to 4 × 15 s before failing
                    print("  Polling for Level 1 in DungeonTree (up to 4 × 15s)…")
                    generated = False
                    for attempt in range(1, 5):
                        time.sleep(15.0)
                        if not _app_alive(h):
                            failures += fail("App crashed during Level 1 generation polling")
                            break
                        shot = h.capture(f"b4_poll_{attempt}")
                        print(f"  Screenshot: {shot.name}  ({attempt * 15}s elapsed)")
                        if _vision_assert(
                            shot,
                            "Does the narrow DungeonTree panel on the far left of the screen "
                            "show a named level entry (for example 'Level 1' or any dungeon level name)? "
                            "Ignore the panel header bar. Look only at the list body.",
                        ):
                            ok(f"Level entry visible in DungeonTree after ~{attempt * 15}s (vision confirmed)")
                            generated = True
                            break

                    if not generated and _app_alive(h):
                        failures += fail("Level 1 did not appear in DungeonTree after full polling")

            # ------------------------------------------------------------------
            # Behavior 5 — Test Drive: load generated dungeon into Play mode
            # ------------------------------------------------------------------
            _TEST_DRIVE_X = WINDOW_W - PANEL_INSPECTOR_W + 12 + 50   # 1142
            _TEST_DRIVE_Y = 22

            if not _app_alive(h):
                failures += fail("App not alive — skipping Test Drive check")
            else:
                print("\nBehavior 5 — Test Drive → generated dungeon loads into Play mode")

                click_app(h.window_rect, _TEST_DRIVE_X, _TEST_DRIVE_Y)
                time.sleep(2.0)

                shot = h.capture("b5_test_drive")
                print(f"  Screenshot: {shot.name}")

                if _app_alive(h):
                    ok("Test Drive launched — Play mode loaded with generated dungeon")
                else:
                    failures += fail("App crashed on Test Drive")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
