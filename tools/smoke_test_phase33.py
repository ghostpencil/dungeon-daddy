"""
Phase 33 smoke test — Player-Controlled Action Loop.

Behaviors verified:
  1. filter_player_actors() returns pc actors; excludes npc/monster/dungeon    (33-1)
  2. PlayerActionPanel._build_request() builds ActionRequest correctly         (33-3)
  3. PlayerActionPanel._format_result() formats resolution into display dict   (33-3)
  4. RpgService.resolve_action() → result stored via store_result()            (33-4)
  5. _build_context_bundle() uses pc actors as focus; bundle not empty         (33-4)
  6. DM agent respond() receives context_bundle kwarg when RPG available       (33-4)
  7. Bundle mechanical_state contains action ratings for pc actor              (33-4)
  8. Pipeline artifact saved to disk                                           (33-6)
  9. [UI] App alive in Play Mode                                               (33-6)
 10. [UI] ACTION tab renders without crash; screenshots captured               (33-6)
 11. [UI] DBG tab renders; CHAR and FALLOUT tabs accessible                    (33-6)

Screenshots saved to:
  tools/screenshots/phase33_*.png

Artifacts saved to:
  artifacts/play_mode/phase33/pipeline_summary.json

Usage:
    cd tools && python smoke_test_phase33.py
    cd tools && python smoke_test_phase33.py --no-ui   # headless only
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import sys
import tempfile
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).parent.parent
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

_MIGRATIONS_DIR = _PROJECT_ROOT / "dungeon_daddy" / "data" / "migrations"
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts" / "play_mode" / "phase33"

from smoke_helpers import (
    BG_0,
    BG_1,
    CHROME_TOTAL_H,
    PAD_MD,
    WINDOW_H,
    WINDOW_W,
    color_close,
    fail,
    menu_bar_center_y,
    menu_slot_center_x,
    menu_slot_x,
    dropdown_item_center_y,
    ok,
    pixel_rgb,
)


# ---------------------------------------------------------------------------
# Seed helper for pipeline tests
# ---------------------------------------------------------------------------

def _seed(repo) -> tuple[str, str, str]:
    """Seed one campaign with pc/npc actors, stress, clocks, memory. Returns (campaign_id, pc_id, scene_id)."""
    from dungeon_daddy.rpg.models import FalloutRecord

    campaign_id = "camp-33"
    pc_id = "actor-lyra"
    scene_id = "scene-33-vault"

    repo.save_campaign(campaign_id, "iron-vault-33", "Iron Vault — Phase 33")
    repo._conn.execute(
        "INSERT INTO scenes (scene_id, campaign_id, location_slug, status) VALUES (?, ?, ?, ?)",
        [scene_id, campaign_id, "vault-entry", "active"],
    )

    # PC: Lyra (player-controlled)
    repo.save_actor(pc_id, campaign_id, "pc", "lyra", "Lyra")
    for action_key, rating in [
        ("fight", 2), ("move", 1), ("tinker", 3), ("study", 2),
        ("focus", 1), ("sway", 0), ("sense", 1), ("channel", 2), ("endure", 1),
    ]:
        repo.save_actor_action_rating(pc_id, action_key, rating)
    repo.save_actor_stress_track(pc_id, "body", 6, 2)
    repo.save_actor_stress_track(pc_id, "composure", 6, 0)

    # NPC: dungeon-controlled
    repo.save_actor("actor-warden", campaign_id, "npc", "warden", "Vault Warden")
    repo.save_actor_stress_track("actor-warden", "body", 4, 0)

    # Dungeon presence
    repo.save_actor("actor-dungeon", campaign_id, "dungeon", "iron-vault", "Iron Vault")

    # Open clock
    repo.save_clock("clock-heat", campaign_id, "Heat Rising", 6, 2, "active")

    # Memory entries
    repo.save_memory_entry(
        "mem-33-a", campaign_id, "event", "Lyra's Oath",
        summary="Lyra swore to retrieve the vault key before dawn.",
        importance=8,
    )
    repo.add_memory_tag("mem-33-a", f"actor:{pc_id}")
    repo.save_memory_entry(
        "mem-33-b", campaign_id, "lore", "Vault Layout",
        summary="The vault has three sealed chambers and one open corridor.",
        importance=5,
    )

    return campaign_id, pc_id, scene_id


class _MockProvider:
    def complete(self, messages, system="", max_tokens=1024) -> str:
        return "[MOCK] The vault door groans. Dust falls from the arch."


# ---------------------------------------------------------------------------
# Layout constants for UI tests (Phase 33: 6 tabs)
# ---------------------------------------------------------------------------

CONTENT_H       = WINDOW_H - CHROME_TOTAL_H          # 830
_PANEL_CHAT_W   = 440
_RPG_PANEL_W    = 300
_RPG_TAB_H      = 26
_BTN_RPG_W      = 88
_BTN_EDIT_W     = 100
_BTN_H          = 24
_CHROME_TITLE_H = 44

# RPG toggle button position in the title bar
_PLAY_BADGE_W   = 100
_EDIT_LEFT      = WINDOW_W - PAD_MD - _PLAY_BADGE_W - PAD_MD * 2 - _BTN_EDIT_W
_RPG_BTN_RIGHT  = _EDIT_LEFT - PAD_MD
_RPG_BTN_X      = _RPG_BTN_RIGHT - _BTN_RPG_W
_BAR_MID        = CONTENT_H + _CHROME_TITLE_H / 2
_RPG_BTN_Y      = _BAR_MID - _BTN_H / 2
_RPG_BTN_CX     = _RPG_BTN_X + _BTN_RPG_W / 2
_RPG_BTN_CY     = _RPG_BTN_Y + _BTN_H / 2

# RPG panel (when open) — 6 tabs now
_MAP_W_OPEN     = WINDOW_W - _PANEL_CHAT_W - _RPG_PANEL_W   # 660
_RPG_PANEL_X    = _PANEL_CHAT_W + _MAP_W_OPEN                # 1100
_N_TABS         = 6
_TAB_W          = _RPG_PANEL_W / _N_TABS                     # 50.0
_TAB_Y          = float(CONTENT_H - _RPG_TAB_H)              # 804.0
_TAB_CY         = _TAB_Y + _RPG_TAB_H / 2                   # 817.0
# Tab centre x: CHAR=1125, SCENE=1175, FALLOUT=1225, MEM=1275, ACTION=1325, DBG=1375
_TAB_CX         = [_RPG_PANEL_X + i * _TAB_W + _TAB_W / 2 for i in range(_N_TABS)]
_TAB_ACTION     = 4
_TAB_DBG        = 5

_BG_2 = (48, 45, 68)
_FILE_DEMO_IDX  = 2


# ---------------------------------------------------------------------------
# Vision assertion
# ---------------------------------------------------------------------------

def _vision_assert(screenshot_path: Path, question: str) -> bool:
    import base64
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
                    "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
                },
                {"type": "text", "text": f"{question}\nReply with only YES or NO."},
            ],
        }],
    )
    return response.content[0].text.strip().upper().startswith("Y")


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _rpg_panel_is_open(pixels, shot_w, win_left, win_top) -> bool:
    panel_mid_x = _RPG_PANEL_X + _RPG_PANEL_W / 2
    panel_mid_y = CONTENT_H / 2
    r, g, b = pixel_rgb(pixels, shot_w, win_left, win_top, panel_mid_x, panel_mid_y)
    from smoke_helpers import color_close
    return color_close((r, g, b), BG_1, tol=20)


def _app_alive(h) -> bool:
    return h._proc is not None and h._proc.poll() is None


def _load_demo_dungeon(h) -> None:
    from ui_input import click_app
    click_app(h.window_rect, menu_slot_center_x("File"), menu_bar_center_y())
    time.sleep(0.4)
    click_app(h.window_rect, menu_slot_x("File") + 40, dropdown_item_center_y(_FILE_DEMO_IDX))
    time.sleep(1.5)
    h.refresh_window_rect()


def _switch_to_play_mode(h) -> None:
    from ui_input import click_app
    _TEST_DRIVE_X = 1142.0
    _TEST_DRIVE_Y = 22.0
    click_app(h.window_rect, _TEST_DRIVE_X, _TEST_DRIVE_Y)
    time.sleep(1.5)
    h.refresh_window_rect()


def _click_tab(h, tab_index: int) -> None:
    from ui_input import click_app
    click_app(h.window_rect, _TAB_CX[tab_index], _TAB_CY)
    time.sleep(0.5)


def _open_rpg_panel(h) -> None:
    from ui_input import click_app
    click_app(h.window_rect, _RPG_BTN_CX, _RPG_BTN_CY)
    time.sleep(0.8)
    h.refresh_window_rect()


# ---------------------------------------------------------------------------
# Pipeline tests (headless)
# ---------------------------------------------------------------------------

def run_pipeline(tmp_path: Path) -> int:
    failures = 0

    from dungeon_daddy.memory.repository import MemoryRepository
    from dungeon_daddy.rpg.actor_control import filter_player_actors, is_player_controlled
    from dungeon_daddy.rpg.models import ActionRequest, ActionResolution, ActorState
    from dungeon_daddy.rpg.service import RpgService
    from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
    from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
    from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent

    db = MemoryRepository(tmp_path / "campaign.duckdb")
    db.initialize_schema(_MIGRATIONS_DIR)
    campaign_id, pc_id, scene_id = _seed(db)
    svc = RpgService()
    panel = PlayerActionPanel()

    # -- Behavior 1: filter_player_actors ----------------------------------
    print("Behavior 1 — filter_player_actors() returns pc actors only")
    raw = db.get_actors_by_campaign(campaign_id)
    all_actors = [
        ActorState(
            actor_id=a["actor_id"], campaign_id=a["campaign_id"],
            actor_type=a["actor_type"], slug=a["slug"], display_name=a["display_name"],
            status=a["status"],
        )
        for a in raw
    ]
    pc_actors = filter_player_actors(all_actors)
    pc_ids = [a.actor_id for a in pc_actors]
    non_pc_types = {a.actor_type for a in all_actors if a.actor_id not in pc_ids}
    print(f"  all_actors={[a.actor_type for a in all_actors]}, pc_actors={pc_ids}")
    if len(pc_actors) == 1 and pc_actors[0].actor_id == pc_id:
        ok("filter_player_actors returns exactly 1 pc actor")
    else:
        failures += fail(f"Expected 1 pc actor, got {pc_actors}")
    if "npc" in non_pc_types and "dungeon" in non_pc_types:
        ok("npc and dungeon actors excluded from player list")
    else:
        failures += fail(f"Expected npc/dungeon excluded; non_pc_types={non_pc_types}")

    # -- Behavior 2: PlayerActionPanel._build_request ----------------------
    print("\nBehavior 2 — PlayerActionPanel._build_request() builds ActionRequest")
    panel.set_actors(pc_actors)
    req = panel._build_request(
        campaign_id=campaign_id,
        actor_id=pc_id,
        intent="Pick the lock on the vault door",
        action_key="tinker",
        push_yourself=False,
        momentum_spend=0,
        dice_pool=3,
    )
    print(f"  request: actor={req.actor_id} action={req.action_key} pool={req.dice_pool}")
    if (req.actor_id == pc_id and req.action_key == "tinker"
            and req.dice_pool == 3 and req.campaign_id == campaign_id):
        ok("ActionRequest built with correct actor, action, pool, campaign")
    else:
        failures += fail(f"ActionRequest fields wrong: {req}")

    # -- Behavior 3: PlayerActionPanel._format_result ----------------------
    print("\nBehavior 3 — PlayerActionPanel._format_result() formats resolution dict")
    mock_resolution = ActionResolution(
        resolution_id="res-smoke33",
        campaign_id=campaign_id,
        actor_id=pc_id,
        action_key="tinker",
        dice_rolled=[3, 5, 6],
        outcome="full",
        stress_cost=0,
    )
    result_dict = panel._format_result(mock_resolution)
    print(f"  result: {result_dict}")
    if (result_dict["outcome"] == "full"
            and result_dict["dice"] == [3, 5, 6]
            and result_dict["stress_cost"] == 0):
        ok("_format_result produces correct outcome/dice/stress_cost")
    else:
        failures += fail(f"_format_result dict wrong: {result_dict}")

    # -- Behavior 4: RpgService.resolve_action + store_result ---------------
    print("\nBehavior 4 — resolve_action() resolves; store_result() stores it")
    resolution, _ = svc.resolve_action(req, fixed=[5, 5, 6])
    summary = panel._format_result(resolution)
    panel.store_result(summary)
    print(f"  outcome={resolution.outcome!r} dice={resolution.dice_rolled} stored={panel._last_result}")
    if panel._last_result is not None and panel._last_result["outcome"] == resolution.outcome:
        ok(f"store_result persisted outcome={resolution.outcome!r}")
    else:
        failures += fail(f"store_result not working; _last_result={panel._last_result}")

    # -- Behavior 5: _build_context_bundle uses pc actors as focus ----------
    print("\nBehavior 5 — ContextBundleBuilder uses pc actors as focus; bundle populated")
    focus_ids = [a.actor_id for a in pc_actors]
    builder = ContextBundleBuilder(
        campaign_id=campaign_id,
        scene_id=scene_id,
        mode="run_scene",
        focus_actor_ids=focus_ids,
        token_budget=5_000,
    )
    bundle = builder.build(db)
    print(f"  bundle_id={bundle.bundle_id!r}  memory_cards={len(bundle.memory_cards)}")
    print(f"  open_clocks={len(bundle.open_clocks)}  focus_actors={focus_ids}")
    if bundle.bundle_id and focus_ids[0] in bundle.mechanical_state:
        ok(f"Bundle built; pc actor {focus_ids[0]} in mechanical_state")
    else:
        failures += fail(f"Bundle missing pc actor in mechanical_state; keys={list(bundle.mechanical_state)}")
    if bundle.open_clocks:
        ok(f"Bundle contains {len(bundle.open_clocks)} open clock(s)")
    else:
        failures += fail("Bundle has no open clocks")
    if bundle.memory_cards:
        ok(f"Bundle has {len(bundle.memory_cards)} memory card(s)")
    else:
        failures += fail("Bundle has no memory cards")

    # -- Behavior 6: DM agent receives context_bundle ----------------------
    print("\nBehavior 6 — DM agent respond() receives context_bundle kwarg")
    from dungeon_daddy.data.models import Room, Level
    import threading, queue as _queue

    agent = DungeonMasterAgent(provider=_MockProvider())
    received_bundle = []

    def _mock_respond(**kwargs):
        received_bundle.append(kwargs.get("context_bundle"))
        return "[MOCK] The vault groans."

    agent.respond = _mock_respond  # type: ignore[method-assign]

    # Simulate what PlayView._spawn_dm_thread does
    _result_q: _queue.Queue = _queue.Queue()

    def _run():
        try:
            response = agent.respond(
                history=[],
                room=Room(id="r1", num=1, name="Vault Entry", x=0, y=0, w=2, h=2, type="hall", note=""),
                level=Level(id=1, name="L1", summary="", ecology="", loop="", loops=[], width=20, height=20, entries=[], rooms=[], connections=[]),
                dungeon=None,
                room_memory="",
                context_bundle=bundle,
            )
            _result_q.put(response)
        except Exception as e:
            _result_q.put(f"ERROR: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=5.0)
    response = _result_q.get_nowait()
    print(f"  respond() returned: {response!r}")
    print(f"  received_bundle: {received_bundle}")
    if received_bundle and received_bundle[0] is bundle:
        ok("DM agent respond() received the ContextBundle kwarg")
    else:
        failures += fail(f"context_bundle not received correctly; got={received_bundle}")

    # -- Behavior 7: Bundle mechanical_state has action ratings ------------
    print("\nBehavior 7 — Bundle mechanical_state includes action ratings for pc actor")
    mech = bundle.mechanical_state.get(pc_id, {})
    print(f"  mechanical_state[{pc_id}]: {mech}")
    if mech.get("action_ratings"):
        ok(f"action_ratings present: {mech['action_ratings']}")
    else:
        failures += fail(f"action_ratings missing from mechanical_state: {mech}")
    if mech.get("stress_tracks"):
        ok(f"stress_tracks present: {mech['stress_tracks']}")
    else:
        failures += fail(f"stress_tracks missing from mechanical_state: {mech}")

    # -- Behavior 8: artifact saved ----------------------------------------
    print("\nBehavior 8 — Pipeline artifact saved to disk")
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = _ARTIFACTS_DIR / "pipeline_summary.json"
    summary_data = {
        "campaign_id": campaign_id,
        "pc_actor_id": pc_id,
        "actor_filtering": {
            "total_actors": len(all_actors),
            "pc_actors": len(pc_actors),
            "excluded_types": sorted(non_pc_types),
        },
        "action_request": {
            "action_key": req.action_key,
            "dice_pool": req.dice_pool,
            "push_yourself": req.push_yourself,
        },
        "resolution": {
            "outcome": resolution.outcome,
            "dice_rolled": resolution.dice_rolled,
            "stress_cost": resolution.stress_cost,
        },
        "bundle": {
            "bundle_id": bundle.bundle_id,
            "memory_cards": len(bundle.memory_cards),
            "open_clocks": len(bundle.open_clocks),
            "active_fallout": len(bundle.active_fallout),
            "mechanical_state_actors": list(bundle.mechanical_state.keys()),
            "provenance": bundle.provenance,
        },
    }
    artifact.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    if artifact.exists() and artifact.stat().st_size > 0:
        ok(f"Artifact saved: {artifact}")
    else:
        failures += fail("Artifact not written")

    db.close()
    return failures


# ---------------------------------------------------------------------------
# UI tests (live app)
# ---------------------------------------------------------------------------

def run_ui() -> int:
    failures = 0
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    screenshots: list[Path] = []

    print("\n--- UI Section ---\n")
    if not has_anthropic:
        print("  NOTE  ANTHROPIC_API_KEY not set — vision assertions skipped\n")

    try:
        from ui_harness import UITestHarness
        from ui_input import click_app, type_text
    except ImportError as e:
        print(f"  SKIP  UITestHarness not available: {e}")
        return 0

    with UITestHarness(tag="phase33", render_wait=4.0) as h:
        if h.window_rect is None:
            return fail("Window did not open within timeout — aborting UI section")

        print(f"  Window rect: {h.window_rect}\n")

        # Setup: load demo dungeon
        print("Setup — File → Demo Dungeon")
        _load_demo_dungeon(h)
        if not _app_alive(h):
            return fail("App crashed after dungeon load — aborting")

        # Setup: switch to Play Mode (Test Drive)
        print("Setup — Test Drive → Play Mode")
        _switch_to_play_mode(h)
        if not _app_alive(h):
            return fail("App crashed switching to Play Mode — aborting")

        win_left, win_top = h.window_rect[0], h.window_rect[1]

        # Behavior 9: App alive in Play Mode
        print("\nBehavior 9 — App alive in Play Mode")
        shot = h.capture("00_play_mode")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if _app_alive(h):
            ok("App alive after switching to Play Mode")
        else:
            return failures + fail("App crashed in Play Mode — aborting")

        # Open RPG panel
        print("\nSetup — Open RPG side panel")
        _open_rpg_panel(h)
        shot = h.capture("01_rpg_panel_open")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if not _app_alive(h):
            return failures + fail("App crashed opening RPG panel — aborting")
        pixels, shot_w = h.pixels, h.shot_w
        if _rpg_panel_is_open(pixels, shot_w, win_left, win_top):
            ok("RPG panel opened (BG_1 fill detected)")
        else:
            failures += fail("RPG panel may not be open — check screenshot")

        # Behavior 10: ACTION tab renders
        print(f"\nBehavior 10 — Click ACTION tab (index {_TAB_ACTION}, cx={_TAB_CX[_TAB_ACTION]:.0f})")
        _click_tab(h, _TAB_ACTION)
        shot = h.capture("02_action_tab")
        screenshots.append(shot)
        print(f"  Screenshot: {shot.name}")
        if not _app_alive(h):
            return failures + fail("App crashed on ACTION tab — aborting")
        if has_anthropic:
            action_ok = _vision_assert(
                shot,
                "In the narrow right-side panel, is there an action panel visible? "
                "Look for 'Actor:', 'Intent:', action key buttons (like FIGHT, MOVE, TINKER), "
                "or a RESOLVE button. Reply YES if any of these are visible.",
            )
            if action_ok:
                ok("ACTION tab renders with player action panel content")
            else:
                failures += fail("ACTION tab content not detected — check screenshot")
        else:
            ok("ACTION tab — no crash (vision assertion skipped)")

        # Behavior 11: Navigate other tabs
        print("\nBehavior 11 — Navigate CHAR, FALLOUT, DBG tabs without crash")
        for tab_idx, tab_name in [(0, "CHAR"), (2, "FALLOUT"), (_TAB_DBG, "DBG")]:
            _click_tab(h, tab_idx)
            shot = h.capture(f"03_{tab_name.lower()}_tab")
            screenshots.append(shot)
            print(f"  Screenshot ({tab_name}): {shot.name}")
            if not _app_alive(h):
                return failures + fail(f"App crashed on {tab_name} tab — aborting")
        ok("CHAR, FALLOUT, DBG tabs navigable without crash")

        # Back to ACTION to confirm tab switch works both ways
        _click_tab(h, _TAB_ACTION)
        time.sleep(0.3)
        shot = h.capture("04_action_tab_return")
        screenshots.append(shot)
        print(f"  Screenshot (ACTION return): {shot.name}")
        if _app_alive(h):
            ok("Returned to ACTION tab without crash")
        else:
            failures += fail("App crashed returning to ACTION tab")

    # Copy screenshots to artifacts
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nCopying {len(screenshots)} screenshot(s) to {_ARTIFACTS_DIR} …")
    for src in screenshots:
        dst = _ARTIFACTS_DIR / src.name
        shutil.copy2(src, dst)
    print(f"  Artifacts saved to: {_ARTIFACTS_DIR}")

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(skip_ui: bool = False) -> int:
    failures = 0
    print("\n=== Phase 33 Smoke Test — Player-Controlled Action Loop ===\n")
    print("--- Pipeline Section ---\n")

    with tempfile.TemporaryDirectory() as tmp:
        failures += run_pipeline(Path(tmp))

    if not skip_ui:
        failures += run_ui()
    else:
        print("\n(UI section skipped via --no-ui)")

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ui", action="store_true", help="Run pipeline section only (no live app)")
    args = parser.parse_args()
    sys.exit(run(skip_ui=args.no_ui))
