"""
Phase 38 smoke test — Chat-Centered RPG Interaction Refactor.

Behaviors verified:
  1.  PlayerActionState: set_actor_roster → actor_id set; cycling works        (38.1)
  2.  PlayerActionState: select_action stores key; invalid key raises           (38.1)
  3.  PlayerActionState: reset clears action_key and intent                     (38.1)
  4.  PlayerActionState: single-actor roster → has_multiple_actors False        (38.1, 38.2)
  5.  PlayerActionState: multi-actor roster → has_multiple_actors True; nav     (38.2)
  6.  build_action_chips: actor with ratings → chips carry correct ratings      (38.3)
  7.  build_action_chips: no actor → all chips have None rating                 (38.3)
  8.  build_actor_mini_card: stress tracks reflected in summary                 (38.2)
  9.  build_actor_mini_card: maxed track triggers has_fallout=True              (38.2)
 10.  format_mechanical_bubble: header contains actor name, action, outcome     (38.6)
 11.  format_mechanical_bubble: with reaction → world reaction lines included   (38.6)
 12.  format_mechanical_bubble: no reaction → no world reaction section         (38.6)
 13.  _on_chat_send + action chip → system bubble with actor name + STUDY       (38.4)
 14.  _on_chat_send + action chip → chat text becomes ActionRequest.intent      (38.4)
 15.  _on_chat_send + action chip → PlayerActionState reset after resolution    (38.4)
 16.  _on_chat_send without chip → no resolution fired (plain chat path)        (38.4)
 17.  _refresh_right_panel_from_actors called at end of _run_chat_action        (38.5)
 18.  Artifact saved to disk                                                    (38.6)

Artifacts saved to:
  artifacts/play_mode/phase38/smoke_summary.json

Usage:
    cd tools && python smoke_test_phase38.py
"""
from __future__ import annotations

import json
import queue
import sys
from pathlib import Path
from unittest.mock import MagicMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts" / "play_mode" / "phase38"

from smoke_helpers import fail, ok  # type: ignore[import]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_actor(
    actor_id: str = "a1",
    display_name: str = "Mara",
    actions: dict | None = None,
    stress: dict | None = None,
) -> ActorState:  # noqa: F821  deferred import under `from __future__ import annotations`
    from dungeon_daddy.rpg.models import ActorState, StressTrack
    if actions is None:
        actions = {"fight": 1, "study": 2, "move": 1}
    if stress is None:
        stress = {"body": StressTrack(track_key="body", capacity=6, filled=2)}
    return ActorState(
        actor_id=actor_id,
        campaign_id="c1",
        actor_type="pc",
        slug=actor_id,
        display_name=display_name,
        actions=actions,
        stress=stress,
    )


def _make_resolution(
    outcome: str = "partial",
    actor_id: str = "a1",
    action_key: str = "study",
    intent: str = "I study the mural",
) -> ActionResolution:  # noqa: F821  deferred import under `from __future__ import annotations`
    from dungeon_daddy.rpg.models import ActionResolution
    return ActionResolution(
        resolution_id="res-1",
        campaign_id="c1",
        actor_id=actor_id,
        action_key=action_key,
        dice_rolled=[3, 5],
        outcome=outcome,
        stress_cost=0,
        intent=intent,
    )


def _make_view_with_chip(
    action_key: str = "study",
    actor_id: str = "a1",
    room_id: str = "r1",
) -> PlayView:  # noqa: F821  deferred import under `from __future__ import annotations`
    from dungeon_daddy.data.models import Level, Room
    from dungeon_daddy.rpg.service import RpgService
    from dungeon_daddy.ui.panels.player_action_panel import PlayerActionPanel
    from dungeon_daddy.ui.player_action_state import PlayerActionState
    from dungeon_daddy.views.play_view import PlayView
    from tests.unit.views._factories import _dungeon, _state

    view = PlayView.__new__(PlayView)

    state = PlayerActionState()
    state.set_actor_roster([actor_id])
    state.actor_id = actor_id
    state.select_action(action_key)
    view._action_state = state

    view._chat = MagicMock()
    view._rpg_service = RpgService()

    panel = PlayerActionPanel()
    panel.set_actors([_make_actor(actor_id=actor_id)])
    view._rpg_action = panel
    view._session.set_actors(panel._actors)
    view._rpg_campaign_id = "c1"
    view._rpg_debug = None
    view._rpg_char = MagicMock()
    view._rpg_fallout = MagicMock()
    view._dm_agent = None
    view._mem_repo = None
    view._result_queue = queue.Queue()
    view._llm_busy = False
    view._active_thread = None
    view._dm_history = []

    room = Room(id=room_id, num=1, name="Hall", x=0, y=0, w=2, h=2, type="hall", note="")
    level = Level(
        id=1, name="L1", summary="", ecology="", loop="",
        loops=[], width=10, height=10, entries=[],
        rooms=[room], connections=[],
    )
    view._dungeon = _dungeon([level])
    view._state = _state(room_id=room_id)

    return view


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> int:
    failures = 0

    from dungeon_daddy.rpg.models import (
        ReactionClockLine,
        ReactionStressLine,
        StressTrack,
        WorldReaction,
    )
    from dungeon_daddy.ui.action_chips import build_action_chips
    from dungeon_daddy.ui.actor_mini_card import build_actor_mini_card
    from dungeon_daddy.ui.mechanical_bubble import format_mechanical_bubble
    from dungeon_daddy.ui.player_action_state import PlayerActionState

    results: dict = {}

    # ------------------------------------------------------------------
    # Behavior 1 — PlayerActionState: roster initialises actor_id
    # ------------------------------------------------------------------
    print("Behavior 1 — set_actor_roster initialises actor_id")
    state = PlayerActionState()
    state.set_actor_roster(["a1", "a2"])
    print(f"  actor_id={state.actor_id}  roster={state._actor_roster}")
    if state.actor_id == "a1" and state._actor_roster == ["a1", "a2"]:
        ok("set_actor_roster: actor_id='a1'")
        results["roster_init"] = True
    else:
        failures += fail(f"Expected actor_id='a1', got {state.actor_id}")
        results["roster_init"] = False

    # ------------------------------------------------------------------
    # Behavior 2 — select_action stores key; invalid key raises
    # ------------------------------------------------------------------
    print("\nBehavior 2 — select_action stores key; invalid key raises ValueError")
    state2 = PlayerActionState()
    state2.select_action("study")
    raised = False
    try:
        state2.select_action("invalid_key")
    except ValueError:
        raised = True
    print(f"  action_key={state2.action_key}  invalid_raised={raised}")
    if state2.action_key == "study" and raised:
        ok("select_action: valid stored; invalid raises ValueError")
        results["select_action"] = True
    else:
        failures += fail(f"select_action wrong: key={state2.action_key}, raised={raised}")
        results["select_action"] = False

    # ------------------------------------------------------------------
    # Behavior 3 — reset clears action_key and intent
    # ------------------------------------------------------------------
    print("\nBehavior 3 — reset() clears action_key and intent")
    state3 = PlayerActionState()
    state3.select_action("fight")
    state3.set_intent("I attack the guardian")
    state3.reset()
    print(f"  action_key={state3.action_key}  intent={state3.intent!r}")
    if state3.action_key is None and state3.intent == "":
        ok("reset(): action_key=None, intent=''")
        results["reset"] = True
    else:
        failures += fail(f"reset() wrong: key={state3.action_key}, intent={state3.intent!r}")
        results["reset"] = False

    # ------------------------------------------------------------------
    # Behavior 4 — single-actor roster → has_multiple_actors False
    # ------------------------------------------------------------------
    print("\nBehavior 4 — single-actor roster → has_multiple_actors=False")
    single = PlayerActionState()
    single.set_actor_roster(["only-a"])
    print(f"  has_multiple_actors={single.has_multiple_actors}")
    if not single.has_multiple_actors:
        ok("Single-actor: has_multiple_actors=False")
        results["single_actor"] = True
    else:
        failures += fail("Single-actor: has_multiple_actors should be False")
        results["single_actor"] = False

    # ------------------------------------------------------------------
    # Behavior 5 — multi-actor roster → nav cycles correctly
    # ------------------------------------------------------------------
    print("\nBehavior 5 — multi-actor roster → prev/next cycling")
    multi = PlayerActionState()
    multi.set_actor_roster(["a1", "a2", "a3"])
    multi.select_next_actor()
    mid = multi.actor_id
    multi.select_next_actor()
    last = multi.actor_id
    multi.select_next_actor()
    wrapped = multi.actor_id
    multi.select_prev_actor()
    back = multi.actor_id
    print(f"  next→{mid}  next→{last}  next→{wrapped}  prev→{back}  multiple={multi.has_multiple_actors}")
    if mid == "a2" and last == "a3" and wrapped == "a1" and back == "a3" and multi.has_multiple_actors:
        ok("Multi-actor cycling: next/prev wrap correctly; has_multiple_actors=True")
        results["multi_actor"] = True
    else:
        failures += fail(
            f"Multi-actor cycling wrong: {mid=}, {last=}, {wrapped=}, {back=}"
        )
        results["multi_actor"] = False

    # ------------------------------------------------------------------
    # Behavior 6 — build_action_chips: actor with ratings → correct chips
    # ------------------------------------------------------------------
    print("\nBehavior 6 — build_action_chips: actor with known ratings")
    actor_with_ratings = _make_actor(actions={"fight": 1, "study": 2, "sense": 3})
    chips = build_action_chips(actor_with_ratings)
    chip_map = {c.action_key: c.rating for c in chips}
    print(f"  fight={chip_map.get('fight')}  study={chip_map.get('study')}  sense={chip_map.get('sense')}  move={chip_map.get('move')}")
    if chip_map.get("fight") == 1 and chip_map.get("study") == 2 and chip_map.get("sense") == 3 and chip_map.get("move") is None:
        ok("build_action_chips: ratings correct; zero-rating omitted as None")
        results["chips_with_ratings"] = True
    else:
        failures += fail(f"build_action_chips wrong: {chip_map}")
        results["chips_with_ratings"] = False

    # ------------------------------------------------------------------
    # Behavior 7 — build_action_chips: no actor → all None ratings
    # ------------------------------------------------------------------
    print("\nBehavior 7 — build_action_chips: no actor → all None ratings")
    chips_no_actor = build_action_chips(None)
    all_none = all(c.rating is None for c in chips_no_actor)
    has_nine = len(chips_no_actor) == 9
    print(f"  count={len(chips_no_actor)}  all_none={all_none}")
    if all_none and has_nine:
        ok("build_action_chips(None): 9 chips, all ratings=None")
        results["chips_no_actor"] = True
    else:
        failures += fail(f"build_action_chips(None) wrong: count={len(chips_no_actor)}, all_none={all_none}")
        results["chips_no_actor"] = False

    # ------------------------------------------------------------------
    # Behavior 8 — build_actor_mini_card: stress tracks in summary
    # ------------------------------------------------------------------
    print("\nBehavior 8 — build_actor_mini_card: stress tracks in summary")
    actor_stress = _make_actor(
        display_name="Lyra",
        stress={
            "body": StressTrack(track_key="body", capacity=6, filled=3),
            "composure": StressTrack(track_key="composure", capacity=4, filled=1),
        },
    )
    card = build_actor_mini_card(actor_stress)
    track_keys = {t[0] for t in card.stress_summary}
    body_track = next((t for t in card.stress_summary if t[0] == "body"), None)
    print(f"  actor_name={card.actor_name}  tracks={track_keys}  body={body_track}  has_fallout={card.has_fallout}")
    if (card.actor_name == "Lyra"
            and "body" in track_keys
            and "composure" in track_keys
            and body_track == ("body", 3, 6)
            and not card.has_fallout):
        ok("build_actor_mini_card: name, tracks, filled/capacity correct; no fallout")
        results["mini_card_stress"] = True
    else:
        failures += fail(f"build_actor_mini_card wrong: {card}")
        results["mini_card_stress"] = False

    # ------------------------------------------------------------------
    # Behavior 9 — build_actor_mini_card: maxed track → has_fallout=True
    # ------------------------------------------------------------------
    print("\nBehavior 9 — build_actor_mini_card: maxed track → has_fallout=True")
    actor_maxed = _make_actor(
        stress={"body": StressTrack(track_key="body", capacity=4, filled=4)},
    )
    card_maxed = build_actor_mini_card(actor_maxed)
    print(f"  has_fallout={card_maxed.has_fallout}")
    if card_maxed.has_fallout:
        ok("Maxed stress track triggers has_fallout=True")
        results["mini_card_fallout"] = True
    else:
        failures += fail(f"Expected has_fallout=True, got {card_maxed.has_fallout}")
        results["mini_card_fallout"] = False

    # ------------------------------------------------------------------
    # Behavior 10 — format_mechanical_bubble: header content
    # ------------------------------------------------------------------
    print("\nBehavior 10 — format_mechanical_bubble: header contains actor name, action, outcome")
    res = _make_resolution(outcome="partial", action_key="study")
    bubble = format_mechanical_bubble("Mara", "study", res)
    first_line = bubble.splitlines()[0]
    print(f"  first_line={first_line!r}")
    if "Mara" in first_line and "STUDY" in first_line and "Partial Success" in first_line and "[5]" in first_line:
        ok("format_mechanical_bubble: header correct (name, action, outcome, best die)")
        results["bubble_header"] = True
    else:
        failures += fail(f"format_mechanical_bubble header wrong: {first_line!r}")
        results["bubble_header"] = False

    # ------------------------------------------------------------------
    # Behavior 11 — format_mechanical_bubble: with reaction → world reaction lines
    # ------------------------------------------------------------------
    print("\nBehavior 11 — format_mechanical_bubble: reaction → world reaction lines")
    reaction = WorldReaction(
        reaction_id="r1",
        campaign_id="c1",
        source_resolution_id="res-1",
        outcome="partial",
        clock_lines=[
            ReactionClockLine(
                clock_id="ck1", label="Heat Rising", ticks=1,
                new_filled=3, new_status="active", reason="partial",
            )
        ],
        stress_lines=[
            ReactionStressLine(
                actor_id="a1", display_name="Mara", track_key="composure",
                amount=1, new_filled=2, reason="partial",
            )
        ],
    )
    bubble_reaction = format_mechanical_bubble("Mara", "study", res, reaction)
    lines = bubble_reaction.splitlines()
    print(f"  lines={lines}")
    has_world = any("World Reaction" in ln for ln in lines)
    has_clock = any("Heat Rising" in ln for ln in lines)
    has_stress = any("composure" in ln for ln in lines)
    if has_world and has_clock and has_stress:
        ok("format_mechanical_bubble: World Reaction section with clock and stress lines")
        results["bubble_reaction"] = True
    else:
        failures += fail(f"bubble_reaction missing content: world={has_world}, clock={has_clock}, stress={has_stress}")
        results["bubble_reaction"] = False

    # ------------------------------------------------------------------
    # Behavior 12 — format_mechanical_bubble: no reaction → no world section
    # ------------------------------------------------------------------
    print("\nBehavior 12 — format_mechanical_bubble: no reaction → no world reaction section")
    bubble_no_reaction = format_mechanical_bubble("Mara", "fight", _make_resolution(outcome="full", action_key="fight"))
    no_world = "World Reaction" not in bubble_no_reaction
    print(f"  no_world_section={no_world}")
    if no_world:
        ok("format_mechanical_bubble without reaction: no World Reaction section")
        results["bubble_no_reaction"] = True
    else:
        failures += fail("format_mechanical_bubble without reaction unexpectedly includes World Reaction")
        results["bubble_no_reaction"] = False

    # ------------------------------------------------------------------
    # Behavior 13 — _on_chat_send + chip → system bubble with actor + action
    # ------------------------------------------------------------------
    print("\nBehavior 13 — _on_chat_send + action chip → system bubble with Mara + STUDY")
    view = _make_view_with_chip(action_key="study")
    view._on_chat_send("I study the ancient mural.")
    msgs = [(c.args[0], c.args[1]) for c in view._chat.add_message.call_args_list]
    system_msgs = [text for role, text in msgs if role == "system"]
    bubble_ok = any("Mara" in t and "STUDY" in t for t in system_msgs)
    print(f"  system_msgs={system_msgs[:2]}")
    if bubble_ok:
        ok("_on_chat_send + chip: system bubble contains 'Mara' and 'STUDY'")
        results["chat_action_bubble"] = True
    else:
        failures += fail(f"Expected system bubble with Mara+STUDY; got: {system_msgs}")
        results["chat_action_bubble"] = False

    # ------------------------------------------------------------------
    # Behavior 14 — chat text becomes ActionRequest.intent
    # ------------------------------------------------------------------
    print("\nBehavior 14 — chat text becomes ActionRequest.intent")
    view14 = _make_view_with_chip(action_key="study")
    captured_resolutions: list = []

    def _spy_reaction(resolution):
        captured_resolutions.append(resolution)

    view14._actions.apply_world_reaction = _spy_reaction  # type: ignore[method-assign]
    view14._on_chat_send("I study the mural to resist its pull.")
    intent_ok = (
        len(captured_resolutions) == 1
        and captured_resolutions[0].intent == "I study the mural to resist its pull."
    )
    print(f"  intent={captured_resolutions[0].intent if captured_resolutions else 'NOT CAPTURED'!r}")
    if intent_ok:
        ok("Chat text becomes ActionRequest.intent")
        results["chat_intent"] = True
    else:
        failures += fail(f"Intent not passed correctly: {captured_resolutions}")
        results["chat_intent"] = False

    # ------------------------------------------------------------------
    # Behavior 15 — PlayerActionState reset after resolution
    # ------------------------------------------------------------------
    print("\nBehavior 15 — PlayerActionState reset after _on_chat_send resolves")
    view15 = _make_view_with_chip(action_key="fight")
    view15._action_state.set_intent("some pending text")
    view15._on_chat_send("I strike the guardian.")
    key_cleared = view15._action_state.action_key is None
    intent_cleared = view15._action_state.intent == ""
    print(f"  action_key={view15._action_state.action_key}  intent={view15._action_state.intent!r}")
    if key_cleared and intent_cleared:
        ok("PlayerActionState reset: action_key=None, intent='' after resolution")
        results["state_reset"] = True
    else:
        failures += fail(f"State not reset: key={view15._action_state.action_key}, intent={view15._action_state.intent!r}")
        results["state_reset"] = False

    # ------------------------------------------------------------------
    # Behavior 16 — No chip → plain chat path, no resolution fired
    # ------------------------------------------------------------------
    print("\nBehavior 16 — No chip selected → plain chat, no resolution")
    view16 = _make_view_with_chip(action_key="study")
    view16._action_state.action_key = None  # override to no chip
    no_chip_resolutions: list = []
    view16._apply_world_reaction = lambda r: no_chip_resolutions.append(r)  # type: ignore[method-assign]
    view16._on_chat_send("Just looking around the room.")
    print(f"  resolutions_fired={len(no_chip_resolutions)}")
    if len(no_chip_resolutions) == 0:
        ok("No chip: plain chat path taken; no resolution fired")
        results["no_chip_plain"] = True
    else:
        failures += fail(f"Plain chat unexpectedly fired {len(no_chip_resolutions)} resolution(s)")
        results["no_chip_plain"] = False

    # ------------------------------------------------------------------
    # Behavior 17 — _refresh_right_panel_from_actors called after _run_chat_action
    # ------------------------------------------------------------------
    print("\nBehavior 17 — _refresh_right_panel_from_actors called after _run_chat_action")

    view17 = _make_view_with_chip(action_key="study")
    refresh_calls: list = []
    original_refresh = view17._refresh_right_panel_from_actors

    def _spy_refresh(actor_id: str) -> None:
        refresh_calls.append(actor_id)
        original_refresh(actor_id)

    view17._refresh_right_panel_from_actors = _spy_refresh  # type: ignore[method-assign]
    view17._on_chat_send("I study the mural.")
    print(f"  refresh_calls={refresh_calls}")
    if len(refresh_calls) == 1 and refresh_calls[0] == "a1":
        ok("_refresh_right_panel_from_actors called once with correct actor_id")
        results["inspector_refresh"] = True
    else:
        failures += fail(f"Expected 1 refresh call for 'a1'; got {refresh_calls}")
        results["inspector_refresh"] = False

    # ------------------------------------------------------------------
    # Behavior 18 — Artifact saved to disk
    # ------------------------------------------------------------------
    print("\nBehavior 18 — Artifact saved to disk")
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = _ARTIFACTS_DIR / "smoke_summary.json"
    artifact.write_text(json.dumps(results, indent=2), encoding="utf-8")
    if artifact.exists() and artifact.stat().st_size > 0:
        ok(f"Artifact saved: {artifact}")
    else:
        failures += fail("Artifact not written")

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 38 Smoke Test — Chat-Centered RPG Interaction Refactor ===\n")
    failures += run_pipeline()
    print(f"\n{'='*58}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*58}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
