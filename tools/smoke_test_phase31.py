"""
Phase 31 smoke test — Context Bundles + AI Integration.

Behaviors verified:
  1. ContextBundleBuilder builds from seeded real DuckDB                   (31-3)
  2. scene_brief populated (location_slug, status)                         (31-3)
  3. mechanical_state populated for focus actor                            (31-3)
  4. memory_cards present; must_remember pins importance>=9 entry          (31-3)
  5. active_fallout and open_clocks populated                              (31-3)
  6. provenance records retrieved / omitted counts                         (31-3)
  7. DMAgent.build_prompt() injects scene brief and memory cards           (31-4)
  8. Bundle JSON artifact saved                                            (31-7)

Artifacts saved to:
  artifacts/play_mode/phase31/bundle_sample.json

Usage:
    cd tools && python smoke_test_phase31.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_MIGRATIONS_DIR = _PROJECT_ROOT / "dungeon_daddy" / "data" / "migrations"
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts" / "play_mode" / "phase31"

from smoke_helpers import fail, ok

from dungeon_daddy.llm.agents.dm_agent import DungeonMasterAgent
from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import FalloutRecord


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed(repo: MemoryRepository) -> None:
    repo.save_campaign("camp-smoke", "smoke-slug", "Smoke Campaign")
    repo._conn.execute(
        "INSERT INTO scenes (scene_id, campaign_id, location_slug, status) VALUES (?, ?, ?, ?)",
        ["scene-smoke", "camp-smoke", "ossuary", "active"],
    )
    repo.save_actor("actor-smoke", "camp-smoke", "pc", "theron", "Theron")
    repo.save_actor_action_rating("actor-smoke", "skirmish", 2)
    repo.save_actor_action_rating("actor-smoke", "study", 1)
    repo.save_actor_stress_track("actor-smoke", "body", 6, 2)
    repo.save_clock("clk-smoke", "camp-smoke", "Ritual of Binding", 8, 5, "active")
    repo.save_fallout_record(FalloutRecord(
        fallout_id="fall-smoke",
        campaign_id="camp-smoke",
        actor_id="actor-smoke",
        track_key="body",
        severity="minor",
        title="Cracked Ribs",
        summary="Took a heavy blow in the ossuary.",
    ))
    # importance >= 9 → must_remember
    repo.save_memory_entry(
        "mem-smoke-1", "camp-smoke", "event", "The Betrayal",
        summary="The guide turned on the party at the bone gate.",
        importance=9,
    )
    # regular entries
    repo.save_memory_entry(
        "mem-smoke-2", "camp-smoke", "lore", "Ossuary Legend",
        summary="The dead here were sealed by an old pact.",
        importance=5,
    )
    repo.save_memory_entry(
        "mem-smoke-3", "camp-smoke", "note", "Party Note",
        summary="Theron suspects the warden is still alive.",
        importance=3,
    )
    # archived — must not appear in cards
    repo.save_memory_entry(
        "mem-smoke-4", "camp-smoke", "event", "Old Rumour",
        summary="A buried rumour, no longer relevant.",
        importance=7,
        status="archived",
    )


# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------

class _MockProvider:
    def complete(self, messages, system="", max_tokens=1024) -> str:
        return "[MOCK] The ossuary stirs. Dust rises from the bone gate."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 31 Smoke Test — Context Bundles + AI Integration ===\n")

    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "campaign.duckdb"
        repo = MemoryRepository(db_path)
        repo.initialize_schema(_MIGRATIONS_DIR)
        _seed(repo)

        # ── Behavior 1: build context bundle ────────────────────────────────
        print("Behavior 1 — ContextBundleBuilder.build() from real DB")
        builder = ContextBundleBuilder(
            campaign_id="camp-smoke",
            scene_id="scene-smoke",
            mode="run_scene",
            focus_actor_ids=["actor-smoke"],
            token_budget=1000,
        )
        bundle = builder.build(repo)
        if bundle.bundle_id:
            ok(f"Bundle built: {bundle.bundle_id}")
        else:
            failures += fail("bundle_id is empty")

        # ── Behavior 2: scene_brief ──────────────────────────────────────────
        print("\nBehavior 2 — scene_brief populated")
        print(f"  scene_brief: {bundle.scene_brief}")
        if bundle.scene_brief.get("location_slug") == "ossuary":
            ok("scene_brief.location_slug == 'ossuary'")
        else:
            failures += fail(f"scene_brief missing or wrong: {bundle.scene_brief}")

        # ── Behavior 3: mechanical_state ─────────────────────────────────────
        print("\nBehavior 3 — mechanical_state populated")
        mech = bundle.mechanical_state.get("actor-smoke", {})
        print(f"  action_ratings: {mech.get('action_ratings')}")
        print(f"  stress_tracks:  {mech.get('stress_tracks')}")
        if mech.get("action_ratings") and mech.get("stress_tracks"):
            ok("mechanical_state has action_ratings and stress_tracks for actor-smoke")
        else:
            failures += fail(f"mechanical_state incomplete: {mech}")

        # ── Behavior 4: memory_cards + must_remember ─────────────────────────
        print("\nBehavior 4 — memory_cards present; must_remember pins importance>=9 entry")
        print(f"  memory_cards ({len(bundle.memory_cards)}):")
        for card in bundle.memory_cards:
            print(f"    [{card['importance']}] {card['title']}")
        print(f"  must_remember: {bundle.must_remember}")
        ids = [c["memory_id"] for c in bundle.memory_cards]
        if "mem-smoke-1" in bundle.must_remember:
            ok("mem-smoke-1 (importance=9) in must_remember")
        else:
            failures += fail("importance>=9 entry missing from must_remember")
        if "mem-smoke-4" not in ids:
            ok("archived entry mem-smoke-4 excluded from memory_cards")
        else:
            failures += fail("archived entry appeared in memory_cards")

        # ── Behavior 5: active_fallout + open_clocks ─────────────────────────
        print("\nBehavior 5 — active_fallout and open_clocks populated")
        print(f"  active_fallout: {bundle.active_fallout}")
        print(f"  open_clocks:    {bundle.open_clocks}")
        if bundle.active_fallout:
            ok(f"active_fallout has {len(bundle.active_fallout)} record(s)")
        else:
            failures += fail("active_fallout is empty")
        if bundle.open_clocks:
            ok(f"open_clocks has {len(bundle.open_clocks)} clock(s)")
        else:
            failures += fail("open_clocks is empty")

        # ── Behavior 6: provenance ───────────────────────────────────────────
        print("\nBehavior 6 — provenance records counts")
        prov = bundle.provenance
        print(f"  provenance: {prov}")
        if prov.get("retrieved", 0) > 0:
            ok(f"provenance.retrieved={prov['retrieved']}, omitted={prov['omitted']}")
        else:
            failures += fail(f"provenance.retrieved is 0 or missing: {prov}")

        # ── Behavior 7: DM prompt contains scene brief ───────────────────────
        print("\nBehavior 7 — DMAgent.build_prompt() injects scene brief and memory")
        agent = DungeonMasterAgent(provider=_MockProvider())
        prompt = agent.build_prompt(bundle)
        print(f"  Prompt (first 200 chars):\n    {prompt[:200]!r}")
        if "ossuary" in prompt:
            ok("Prompt contains scene location 'ossuary'")
        else:
            failures += fail("Prompt does not contain scene location 'ossuary'")
        if "The Betrayal" in prompt:
            ok("Prompt contains memory card title 'The Betrayal'")
        else:
            failures += fail("Prompt does not contain memory card 'The Betrayal'")

        # ── Behavior 8: save artifact ────────────────────────────────────────
        print("\nBehavior 8 — Save bundle JSON artifact")
        artifact = _ARTIFACTS_DIR / "bundle_sample.json"
        artifact.write_text(
            json.dumps(bundle.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )
        if artifact.exists() and artifact.stat().st_size > 0:
            ok(f"Bundle artifact saved: {artifact}")
        else:
            failures += fail("Bundle artifact not written")

        repo.close()

    print(f"\n{'='*40}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*40}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
