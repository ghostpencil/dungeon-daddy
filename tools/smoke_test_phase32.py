"""
Phase 32 smoke test — Stabilization + Balancing.

Behaviors verified:
  1. Action roll with push_yourself yields stress_cost = 1              (32-6)
  2. Stress applied to body track — filled incremented                  (32-6)
  3. FalloutEngine produces a fallout record; track resets              (32-6)
  4. Memory entry referencing fallout saved to repo                     (32-6)
  5. ContextBundleBuilder includes new memory card                      (32-6)
  6. DMAgent.build_prompt() contains fallout title                      (32-6)
  7. Pipeline artifact saved to disk                                    (32-6)

Artifacts saved to:
  artifacts/play_mode/phase32/pipeline_summary.json

Usage:
    cd tools && python smoke_test_phase32.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_MIGRATIONS_DIR = _PROJECT_ROOT / "dungeon_daddy" / "data" / "migrations"
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts" / "play_mode" / "phase32"

from smoke_helpers import fail, ok

from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.fallout import evaluate_fallout
from dungeon_daddy.rpg.models import ActionRequest, ActorState, StressTrack
from dungeon_daddy.rpg.service import RpgService

sys.path.insert(0, str(_PROJECT_ROOT / "tests"))
from fixtures.phase32_campaign import CAMPAIGN_ID, SABLE_ID, SCENE_COMBAT_ID, seed_campaign


class _MockProvider:
    def complete(self, messages, system="", max_tokens=1024) -> str:
        return "[MOCK] The forge-floor shudders. Iron dust hangs in the air."


def run() -> int:
    failures = 0
    print("\n=== Phase 32 Smoke Test — RPG + Memory Full Pipeline ===\n")

    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        db = MemoryRepository(Path(tmp) / "campaign.duckdb")
        db.initialize_schema(_MIGRATIONS_DIR)
        seed_campaign(db)
        svc = RpgService()

        # ── Behavior 1: action roll → stress_cost ───────────────────────────
        print("Behavior 1 — action roll with push_yourself yields stress_cost = 1")
        request = ActionRequest(
            campaign_id=CAMPAIGN_ID,
            actor_id=SABLE_ID,
            action_key="skirmish",
            scene_id=SCENE_COMBAT_ID,
            dice_pool=2,
            push_yourself=True,
        )
        # fixed=[1,1,1] forces a miss so this test is deterministic
        resolution, _ = svc.resolve_action(request, fixed=[1, 1, 1])
        print(f"  outcome={resolution.outcome!r}  stress_cost={resolution.stress_cost}")
        if resolution.stress_cost == 1:
            ok("stress_cost == 1 from push_yourself")
        else:
            failures += fail(f"stress_cost expected 1, got {resolution.stress_cost}")

        # ── Behavior 2: apply stress → track incremented ─────────────────────
        print("\nBehavior 2 — stress applied to body track (3 → 4)")
        body = StressTrack(track_key="body", capacity=6, filled=3)
        body_after, _ = svc.apply_stress(
            SABLE_ID, CAMPAIGN_ID, body, amount=resolution.stress_cost
        )
        db.save_actor_stress_track(SABLE_ID, "body", body_after.capacity, body_after.filled)
        print(f"  body.filled: {body.filled} → {body_after.filled}")
        if body_after.filled == 4:
            ok("body.filled incremented to 4")
        else:
            failures += fail(f"body.filled expected 4, got {body_after.filled}")

        # ── Behavior 3: fill track → trigger fallout ─────────────────────────
        print("\nBehavior 3 — fill body track and trigger fallout")
        body_full, _ = svc.apply_stress(SABLE_ID, CAMPAIGN_ID, body_after, amount=2)
        db.save_actor_stress_track(SABLE_ID, "body", body_full.capacity, body_full.filled)
        sable = ActorState(
            actor_id=SABLE_ID,
            campaign_id=CAMPAIGN_ID,
            actor_type="pc",
            slug="sable",
            display_name="Sable",
            stress={"body": body_full},
        )
        new_fallout, reset_body = evaluate_fallout(
            sable, "body", CAMPAIGN_ID, existing_fallout=None
        )
        db.save_fallout_record(new_fallout)
        db.save_actor_stress_track(SABLE_ID, "body", reset_body.capacity, reset_body.filled)
        print(f"  fallout: {new_fallout.title!r} ({new_fallout.severity})")
        print(f"  body reset to {reset_body.filled}/{reset_body.capacity}")
        records = db.get_fallout_records(CAMPAIGN_ID, SABLE_ID)
        if any(r["fallout_id"] == new_fallout.fallout_id for r in records):
            ok(f"Fallout record '{new_fallout.title}' persisted in repo")
        else:
            failures += fail("Fallout record not found in repo")

        # ── Behavior 4: memory entry referencing fallout ──────────────────────
        print("\nBehavior 4 — memory entry referencing fallout event")
        new_memory_id = f"mem-smoke32-{uuid.uuid4()}"
        db.save_memory_entry(
            new_memory_id,
            CAMPAIGN_ID,
            "event",
            f"Fallout: {new_fallout.title}",
            summary=(
                f"Sable suffered {new_fallout.title} after the forge-floor confrontation."
            ),
            importance=7,
        )
        db.add_memory_tag(new_memory_id, f"actor:{SABLE_ID}")
        entry = db.get_memory_entry(new_memory_id)
        if entry and entry["memory_id"] == new_memory_id:
            ok(f"Memory entry '{entry['title']}' saved (importance={entry['importance']})")
        else:
            failures += fail("Memory entry not found in repo")

        # ── Behavior 5: context bundle includes new memory card ───────────────
        print("\nBehavior 5 — context bundle includes new memory card")
        bundle = ContextBundleBuilder(
            CAMPAIGN_ID, SCENE_COMBAT_ID, "run_scene", [SABLE_ID], 10_000
        ).build(db)
        card_ids = {c["memory_id"] for c in bundle.memory_cards}
        print(f"  memory_cards ({len(bundle.memory_cards)}):")
        for card in bundle.memory_cards:
            print(f"    [{card['importance']}] {card['title']}")
        if new_memory_id in card_ids:
            ok(f"New memory card present in bundle ({len(bundle.memory_cards)} total)")
        else:
            failures += fail("New memory card not found in bundle")

        # ── Behavior 6: DM prompt contains fallout title ──────────────────────
        print("\nBehavior 6 — DMAgent.build_prompt() contains fallout title")
        agent = DungeonMasterAgent(provider=_MockProvider())
        prompt = agent.build_prompt(bundle)
        print(f"  Prompt snippet (first 300 chars):\n    {prompt[:300]!r}")
        if new_fallout.title in prompt:
            ok(f"Prompt contains fallout title {new_fallout.title!r}")
        else:
            failures += fail(f"Prompt missing fallout title {new_fallout.title!r}")
        if "Active Fallout" in prompt:
            ok("Prompt contains 'Active Fallout' section header")
        else:
            failures += fail("Prompt missing 'Active Fallout' section header")

        # ── Behavior 7: save pipeline artifact ───────────────────────────────
        print("\nBehavior 7 — Save pipeline summary artifact")
        artifact = _ARTIFACTS_DIR / "pipeline_summary.json"
        summary = {
            "campaign_id": CAMPAIGN_ID,
            "action_roll": {
                "resolution_id": resolution.resolution_id,
                "outcome": resolution.outcome,
                "stress_cost": resolution.stress_cost,
                "dice_rolled": resolution.dice_rolled,
            },
            "stress": {
                "body_before": body.filled,
                "body_after_action": body_after.filled,
                "body_filled": body_full.filled,
                "body_reset": reset_body.filled,
            },
            "fallout": {
                "fallout_id": new_fallout.fallout_id,
                "title": new_fallout.title,
                "severity": new_fallout.severity,
                "track_key": new_fallout.track_key,
            },
            "memory": {
                "memory_id": new_memory_id,
                "title": f"Fallout: {new_fallout.title}",
                "in_bundle": new_memory_id in card_ids,
            },
            "bundle": {
                "bundle_id": bundle.bundle_id,
                "memory_cards": len(bundle.memory_cards),
                "active_fallout": len(bundle.active_fallout),
                "open_clocks": len(bundle.open_clocks),
            },
            "prompt_length": len(prompt),
        }
        artifact.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if artifact.exists() and artifact.stat().st_size > 0:
            ok(f"Artifact saved: {artifact}")
        else:
            failures += fail("Artifact not written")

        db.close()

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
