"""
Phase 37 smoke test — Memory Approval and Playtest Curation.

Behaviors verified:
  1.  Crucible seed pack applies; all seeded memories are approved       (37-seed)
  2.  Tomb seed pack applies; all seeded memories are approved           (37-seed)
  3.  Draft memory saved via save_memory_entry() defaults to 'draft'     (37-1)
  4.  MemoryRetriever.query() excludes draft by default                  (37-2)
  5.  update_memory_status(approved) → appears in default retrieval      (37-3)
  6.  update_memory_status(rejected) → still excluded from retrieval     (37-3)
  7.  include_archived=True returns all statuses                         (37-2)
  8.  count_by_status() reflects correct per-status breakdown            (37-4)
  9.  build_curation_report() covers both campaigns accurately           (37-4)
 10.  MemoryInspectorPanel.approve_selected() → status approved,         (37-5)
     pending_commit set
 11.  MemoryInspectorPanel.reject_selected() → status rejected,          (37-5)
     pending_commit set
 12.  MemoryInspectorPanel.edit_selected_summary() → summary updated,    (37-5)
     pending_commit set
 13.  MemoryInspectorPanel.pop_pending_commit() returns entry + clears   (37-5)
 14.  Artifact saved to disk                                             (37-6)

Artifacts saved to:
  artifacts/play_mode/phase37/playtest_summary.json

Usage:
    cd tools && python smoke_test_phase37.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_MIGRATIONS_DIR = _PROJECT_ROOT / "dungeon_daddy" / "data" / "migrations"
_SEED_DIR = _PROJECT_ROOT / "seed_data" / "campaigns"
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts" / "play_mode" / "phase37"

from smoke_helpers import fail, ok  # type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_repo(db_path: Path):
    from dungeon_daddy.memory.repository import MemoryRepository
    repo = MemoryRepository(db_path)
    repo.initialize_schema(_MIGRATIONS_DIR)
    return repo


def _load_and_apply(campaign_id: str, seed_name: str, repo) -> int:
    from dungeon_daddy.rpg.seed_pack import apply_seed_pack, load_seed_pack
    pack = load_seed_pack(_SEED_DIR / seed_name / "rpg_seed.json")
    repo.save_campaign(campaign_id, pack.campaign_slug, pack.campaign_slug.replace("-", " ").title())
    result = apply_seed_pack(pack, campaign_id, repo, _MIGRATIONS_DIR)
    return result.memories_applied


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(tmp_path: Path) -> int:
    failures = 0

    from dungeon_daddy.memory.curation import build_curation_report
    from dungeon_daddy.memory.models import MemoryEntry
    from dungeon_daddy.memory.retrieval import MemoryRetriever
    from dungeon_daddy.ui.panels.memory_inspector_panel import MemoryInspectorPanel

    repo = _open_repo(tmp_path / "campaign.duckdb")

    crucible_id = "camp-crucible"
    tomb_id = "camp-tomb"

    # ------------------------------------------------------------------
    # Behavior 1 — Crucible seed: all memories approved
    # ------------------------------------------------------------------
    print("Behavior 1 — Crucible seed pack applied; seeded memories are approved")
    crucible_count = _load_and_apply(crucible_id, "the-crucible", repo)
    entries = repo.get_memory_entries_by_campaign(crucible_id)
    non_approved = [e for e in entries if e["status"] != "approved"]
    print(f"  seeded={crucible_count}  non_approved={len(non_approved)}")
    if crucible_count > 0 and len(non_approved) == 0:
        ok(f"Crucible: {crucible_count} memories seeded; all approved")
    else:
        failures += fail(f"Crucible seed: {crucible_count} memories, {len(non_approved)} non-approved: {non_approved}")

    # ------------------------------------------------------------------
    # Behavior 2 — Tomb seed: all memories approved
    # ------------------------------------------------------------------
    print("\nBehavior 2 — Tomb seed pack applied; seeded memories are approved")
    tomb_count = _load_and_apply(tomb_id, "tomb-of-the-forgotten-king", repo)
    entries_tomb = repo.get_memory_entries_by_campaign(tomb_id)
    non_approved_tomb = [e for e in entries_tomb if e["status"] != "approved"]
    print(f"  seeded={tomb_count}  non_approved={len(non_approved_tomb)}")
    if tomb_count > 0 and len(non_approved_tomb) == 0:
        ok(f"Tomb: {tomb_count} memories seeded; all approved")
    else:
        failures += fail(f"Tomb seed: {tomb_count} memories, {len(non_approved_tomb)} non-approved: {non_approved_tomb}")

    # ------------------------------------------------------------------
    # Behavior 3 — save_memory_entry() defaults to draft
    # ------------------------------------------------------------------
    print("\nBehavior 3 — save_memory_entry() defaults to 'draft'")
    repo.save_memory_entry(
        "mem-draft-1", crucible_id, "event", "LLM Draft Memory",
        summary="Kira triggered the forge alarm by touching the rune panel.",
        importance=6,
    )
    raw = repo.get_memory_entries_by_campaign(crucible_id)
    draft_entry = next((e for e in raw if e["memory_id"] == "mem-draft-1"), None)
    print(f"  status={draft_entry['status'] if draft_entry else 'NOT FOUND'}")
    if draft_entry and draft_entry["status"] == "draft":
        ok("save_memory_entry() defaults to 'draft'")
    else:
        failures += fail(f"Expected status='draft', got {draft_entry}")

    # ------------------------------------------------------------------
    # Behavior 4 — default retrieval excludes draft
    # ------------------------------------------------------------------
    print("\nBehavior 4 — MemoryRetriever.query() excludes draft by default")
    retriever = MemoryRetriever(repo, crucible_id)
    default_results = retriever.query()
    draft_ids_in_results = [e.memory_id for e in default_results if e.status == "draft"]
    approved_count = len([e for e in default_results if e.status == "approved"])
    print(f"  approved={approved_count}  draft_leaked={len(draft_ids_in_results)}")
    if len(draft_ids_in_results) == 0 and approved_count == crucible_count:
        ok(f"Default query returns {approved_count} approved; 0 drafts leaked")
    else:
        failures += fail(f"Draft leaked into default query: {draft_ids_in_results}")

    # ------------------------------------------------------------------
    # Behavior 5 — approve draft → appears in default retrieval
    # ------------------------------------------------------------------
    print("\nBehavior 5 — update_memory_status(approved) → appears in retrieval")
    repo.update_memory_status("mem-draft-1", "approved")
    after_approve = retriever.query()
    ids_after = {e.memory_id for e in after_approve}
    print(f"  mem-draft-1 in results: {'mem-draft-1' in ids_after}")
    if "mem-draft-1" in ids_after:
        ok("Approved draft now appears in default retrieval")
    else:
        failures += fail("Approved draft not appearing in default retrieval")

    # ------------------------------------------------------------------
    # Behavior 6 — reject second draft → stays excluded
    # ------------------------------------------------------------------
    print("\nBehavior 6 — update_memory_status(rejected) → excluded from retrieval")
    repo.save_memory_entry(
        "mem-draft-2", crucible_id, "event", "Rejected Memory",
        summary="Talvas found a hidden passage — false lead.",
        importance=3,
    )
    repo.update_memory_status("mem-draft-2", "rejected")
    after_reject = retriever.query()
    rejected_in_results = [e.memory_id for e in after_reject if e.memory_id == "mem-draft-2"]
    print(f"  mem-draft-2 in results: {bool(rejected_in_results)}")
    if not rejected_in_results:
        ok("Rejected memory excluded from default retrieval")
    else:
        failures += fail("Rejected memory appeared in default retrieval")

    # ------------------------------------------------------------------
    # Behavior 7 — include_archived=True returns all statuses
    # ------------------------------------------------------------------
    print("\nBehavior 7 — include_archived=True returns all statuses")
    all_results = retriever.query(include_archived=True)
    all_ids = {e.memory_id for e in all_results}
    statuses_found = {e.status for e in all_results}
    print(f"  total={len(all_results)}  statuses={statuses_found}")
    if "mem-draft-2" in all_ids and "rejected" in statuses_found:
        ok(f"include_archived=True returns {len(all_results)} entries including rejected")
    else:
        failures += fail(f"include_archived=True missing rejected entries; ids={all_ids}")

    # ------------------------------------------------------------------
    # Behavior 8 — count_by_status() per campaign
    # ------------------------------------------------------------------
    print("\nBehavior 8 — count_by_status() reflects per-status breakdown")
    crucible_counts = repo.count_by_status(crucible_id)
    tomb_counts = repo.count_by_status(tomb_id)
    print(f"  crucible={crucible_counts}")
    print(f"  tomb={tomb_counts}")
    expected_crucible_approved = crucible_count + 1  # seeded + mem-draft-1 promoted
    if (crucible_counts.get("approved", 0) == expected_crucible_approved
            and crucible_counts.get("rejected", 0) == 1
            and tomb_counts.get("approved", 0) == tomb_count):
        ok(f"count_by_status correct: crucible approved={crucible_counts['approved']}, "
           f"rejected={crucible_counts['rejected']}; tomb approved={tomb_counts['approved']}")
    else:
        failures += fail(
            f"count_by_status mismatch: crucible={crucible_counts} "
            f"(expected approved={expected_crucible_approved}, rejected=1); "
            f"tomb={tomb_counts} (expected approved={tomb_count})"
        )

    # ------------------------------------------------------------------
    # Behavior 9 — build_curation_report() covers both campaigns
    # ------------------------------------------------------------------
    print("\nBehavior 9 — build_curation_report() covers both campaigns")
    report = build_curation_report(repo, [crucible_id, tomb_id])
    print(f"  campaigns_in_report={[r['campaign_id'] for r in report]}")
    crucible_rep = next((r for r in report if r["campaign_id"] == crucible_id), None)
    tomb_rep = next((r for r in report if r["campaign_id"] == tomb_id), None)
    if crucible_rep and tomb_rep:
        ok(f"Report covers both campaigns; crucible counts={crucible_rep['counts']}; "
           f"tomb counts={tomb_rep['counts']}")
    else:
        failures += fail(f"Report missing campaigns: {[r['campaign_id'] for r in report]}")
    if crucible_rep and len(crucible_rep["drafts"]) == 0:
        ok("Crucible report has 0 pending drafts (mem-draft-1 approved, mem-draft-2 rejected)")
    elif crucible_rep:
        failures += fail(f"Crucible report drafts non-empty: {crucible_rep['drafts']}")

    # ------------------------------------------------------------------
    # Behavior 10 — MemoryInspectorPanel.approve_selected()
    # ------------------------------------------------------------------
    print("\nBehavior 10 — MemoryInspectorPanel.approve_selected() workflow")
    panel = MemoryInspectorPanel()
    draft_e = MemoryEntry(
        memory_id="panel-draft-a", campaign_id=crucible_id,
        type="event", title="Panel Draft A",
        summary="The ward collapsed when Mira crossed the threshold.",
        status="draft", importance=6,
    )
    panel.set_entries([draft_e])
    panel.select_entry(draft_e)
    panel.approve_selected()
    sel = panel._selected
    pending = panel._pending_commit
    in_list = next((e for e in panel._entries if e.memory_id == "panel-draft-a"), None)
    print(f"  selected.status={sel.status if sel else None}  pending.memory_id={pending.memory_id if pending else None}")
    if sel and sel.status == "approved" and pending and pending.memory_id == "panel-draft-a":
        ok("approve_selected: status=approved, pending_commit set")
    else:
        failures += fail(f"approve_selected wrong state: selected={sel}, pending={pending}")
    if in_list and in_list.status == "approved":
        ok("approve_selected: entry list updated")
    else:
        failures += fail(f"approve_selected: entry not updated in list: {in_list}")

    # ------------------------------------------------------------------
    # Behavior 11 — MemoryInspectorPanel.reject_selected()
    # ------------------------------------------------------------------
    print("\nBehavior 11 — MemoryInspectorPanel.reject_selected() workflow")
    panel2 = MemoryInspectorPanel()
    draft_b = MemoryEntry(
        memory_id="panel-draft-b", campaign_id=crucible_id,
        type="event", title="Panel Draft B",
        summary="Golem A-7 made eye contact with Kira for three seconds.",
        status="draft", importance=5,
    )
    panel2.set_entries([draft_b])
    panel2.select_entry(draft_b)
    panel2.reject_selected()
    sel2 = panel2._selected
    pending2 = panel2._pending_commit
    print(f"  selected.status={sel2.status if sel2 else None}  pending.memory_id={pending2.memory_id if pending2 else None}")
    if sel2 and sel2.status == "rejected" and pending2 and pending2.memory_id == "panel-draft-b":
        ok("reject_selected: status=rejected, pending_commit set")
    else:
        failures += fail(f"reject_selected wrong state: selected={sel2}, pending={pending2}")

    # ------------------------------------------------------------------
    # Behavior 12 — MemoryInspectorPanel.edit_selected_summary()
    # ------------------------------------------------------------------
    print("\nBehavior 12 — MemoryInspectorPanel.edit_selected_summary() workflow")
    panel3 = MemoryInspectorPanel()
    draft_c = MemoryEntry(
        memory_id="panel-draft-c", campaign_id=crucible_id,
        type="event", title="Panel Draft C",
        summary="[rough draft]",
        status="draft", importance=4,
    )
    panel3.set_entries([draft_c])
    panel3.select_entry(draft_c)
    new_summary = "Kira found a dwarven inscription above the second gate: 'Those who endure may pass.'"
    panel3.edit_selected_summary(new_summary)
    sel3 = panel3._selected
    pending3 = panel3._pending_commit
    print(f"  selected.summary={sel3.summary[:40] + '...' if sel3 and len(sel3.summary) > 40 else sel3.summary if sel3 else None}")
    if sel3 and sel3.summary == new_summary and pending3 and pending3.summary == new_summary:
        ok("edit_selected_summary: summary updated, pending_commit set")
    else:
        failures += fail(f"edit_selected_summary wrong state: summary={sel3.summary if sel3 else None}")

    # ------------------------------------------------------------------
    # Behavior 13 — MemoryInspectorPanel.pop_pending_commit()
    # ------------------------------------------------------------------
    print("\nBehavior 13 — MemoryInspectorPanel.pop_pending_commit() returns + clears")
    popped = panel3.pop_pending_commit()
    still_pending = panel3._pending_commit
    print(f"  popped.memory_id={popped.memory_id if popped else None}  pending_after={still_pending}")
    if popped and popped.memory_id == "panel-draft-c" and still_pending is None:
        ok("pop_pending_commit returns entry and clears pending_commit")
    else:
        failures += fail(f"pop_pending_commit: popped={popped}, still_pending={still_pending}")
    second_pop = panel3.pop_pending_commit()
    if second_pop is None:
        ok("Second pop_pending_commit returns None (idempotent)")
    else:
        failures += fail(f"Second pop returned non-None: {second_pop}")

    # ------------------------------------------------------------------
    # Behavior 14 — artifact saved
    # ------------------------------------------------------------------
    print("\nBehavior 14 — Artifact saved to disk")
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = _ARTIFACTS_DIR / "playtest_summary.json"
    summary_data = {
        "campaigns": {
            crucible_id: {
                "seeded_memories": crucible_count,
                "status_counts": crucible_counts,
                "curation_report_drafts": len(crucible_rep["drafts"]) if crucible_rep else None,
            },
            tomb_id: {
                "seeded_memories": tomb_count,
                "status_counts": tomb_counts,
                "curation_report_drafts": len(tomb_rep["drafts"]) if tomb_rep else None,
            },
        },
        "retrieval": {
            "default_returns_approved_only": len(draft_ids_in_results) == 0,
            "approved_count_after_approve": len(after_approve),
            "rejected_excluded": not bool(rejected_in_results),
            "include_archived_all_statuses": sorted(statuses_found),
        },
        "inspector_panel": {
            "approve_selected": sel.status == "approved" if sel else False,
            "reject_selected": sel2.status == "rejected" if sel2 else False,
            "edit_summary": sel3.summary == new_summary if sel3 else False,
            "pop_clears_pending": still_pending is None,
        },
    }
    artifact.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    if artifact.exists() and artifact.stat().st_size > 0:
        ok(f"Artifact saved: {artifact}")
    else:
        failures += fail("Artifact not written")

    repo.close()
    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    failures = 0
    print("\n=== Phase 37 Smoke Test — Memory Approval and Playtest Curation ===\n")

    with tempfile.TemporaryDirectory() as tmp:
        failures += run_pipeline(Path(tmp))

    print(f"\n{'='*56}")
    if failures == 0:
        print("ALL BEHAVIORS PASSED")
    else:
        print(f"{failures} BEHAVIOR(S) FAILED")
    print(f"{'='*56}\n")
    return failures


if __name__ == "__main__":
    sys.exit(run())
