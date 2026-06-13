"""Export a campaign's full state to a JSON-serializable dict.

Raw state export (default):
    python tools/export_campaign.py campaigns/the-crucible/campaign.duckdb campaign:the-crucible

Manifest export (CampaignManifest schema):
    python tools/export_campaign.py campaigns/the-crucible/campaign.duckdb campaign:the-crucible --manifest
    python tools/export_campaign.py campaigns/the-crucible/campaign.duckdb campaign:the-crucible --manifest --out manifest.json
"""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository


def export_campaign(repo: MemoryRepository, campaign_id: str) -> dict:
    """Return a JSON-serialisable bundle of all campaign state."""
    conn = repo._conn
    assert conn is not None

    campaign = repo.get_campaign(campaign_id)

    actor_rows = conn.execute(
        """
        SELECT actor_id, campaign_id, actor_type, slug, display_name, status
        FROM actors WHERE campaign_id = ?
        """,
        [campaign_id],
    ).fetchall()
    actors = []
    for row in actor_rows:
        actor_id = row[0]
        actors.append(
            {
                "actor_id": actor_id,
                "campaign_id": row[1],
                "actor_type": row[2],
                "slug": row[3],
                "display_name": row[4],
                "status": row[5],
                "action_ratings": repo.get_actor_action_ratings(actor_id),
                "stress_tracks": repo.get_actor_stress_tracks(actor_id),
            }
        )

    clocks = repo.get_clocks(campaign_id)

    fallout_rows = conn.execute(
        """
        SELECT fallout_id, campaign_id, actor_id, track_key, severity,
               title, summary, status
        FROM fallout WHERE campaign_id = ?
        """,
        [campaign_id],
    ).fetchall()
    fallout = [
        {
            "fallout_id": r[0],
            "campaign_id": r[1],
            "actor_id": r[2],
            "track_key": r[3],
            "severity": r[4],
            "title": r[5],
            "summary": r[6],
            "status": r[7],
        }
        for r in fallout_rows
    ]

    entries = repo.get_memory_entries_by_campaign(campaign_id)
    for entry in entries:
        entry["tags"] = repo.get_memory_tags(entry["memory_id"])

    scene_rows = conn.execute(
        """
        SELECT scene_id, campaign_id, location_slug, status
        FROM scenes WHERE campaign_id = ?
        """,
        [campaign_id],
    ).fetchall()
    scenes = [
        {
            "scene_id": r[0],
            "campaign_id": r[1],
            "location_slug": r[2],
            "status": r[3],
        }
        for r in scene_rows
    ]

    return {
        "campaign": campaign,
        "actors": actors,
        "clocks": clocks,
        "fallout": fallout,
        "memory_entries": entries,
        "scenes": scenes,
    }


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Export campaign state to JSON")
    parser.add_argument("db_path", help="Path to campaign.duckdb")
    parser.add_argument("campaign_id", help="Campaign ID to export")
    parser.add_argument("--out", help="Output file (default: stdout)")
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Export as CampaignManifest JSON (Phase 40 schema) instead of raw state bundle",
    )
    args = parser.parse_args()

    _MIGRATIONS = (
        Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"
    )
    r = MemoryRepository(Path(args.db_path))
    r.initialize_schema(_MIGRATIONS)

    if args.manifest:
        from dungeon_daddy.campaign.exporter import export_campaign_manifest
        manifest = export_campaign_manifest(args.campaign_id, r)
        r.close()
        output = json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False)
    else:
        bundle = export_campaign(r, args.campaign_id)
        r.close()
        output = json.dumps(bundle, indent=2, default=str)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Exported to {args.out}")
    else:
        print(output)
