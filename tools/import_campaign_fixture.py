"""Import a campaign JSON bundle into a MemoryRepository."""
from __future__ import annotations

import json
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import FalloutRecord


def import_campaign_fixture(repo: MemoryRepository, bundle: dict) -> None:
    """Seed *repo* from a bundle produced by export_campaign."""
    c = bundle["campaign"]
    repo.save_campaign(
        c["campaign_id"],
        c["slug"],
        c["title"],
        status=c.get("status", "active"),
        dungeon_slug=c.get("dungeon_slug"),
    )

    for actor in bundle.get("actors", []):
        repo.save_actor(
            actor["actor_id"],
            actor["campaign_id"],
            actor["actor_type"],
            actor["slug"],
            actor["display_name"],
            actor.get("status", "active"),
        )
        for ar in actor.get("action_ratings", []):
            repo.save_actor_action_rating(
                actor["actor_id"], ar["action_key"], ar["rating"]
            )
        for st in actor.get("stress_tracks", []):
            repo.save_actor_stress_track(
                actor["actor_id"], st["track_key"], st["capacity"], st["filled"]
            )

    for clock in bundle.get("clocks", []):
        repo.save_clock(
            clock["clock_id"],
            clock["campaign_id"],
            clock["label"],
            clock["segments"],
            clock["filled"],
            clock.get("status", "active"),
        )

    for f in bundle.get("fallout", []):
        repo.save_fallout_record(
            FalloutRecord(
                fallout_id=f["fallout_id"],
                campaign_id=f["campaign_id"],
                actor_id=f["actor_id"],
                track_key=f["track_key"],
                severity=f["severity"],
                title=f["title"],
                summary=f["summary"],
                status=f.get("status", "active"),
            )
        )

    for entry in bundle.get("memory_entries", []):
        repo.save_memory_entry(
            entry["memory_id"],
            entry["campaign_id"],
            entry["type"],
            entry["title"],
            summary=entry.get("summary", ""),
            status=entry.get("status", "active"),
            importance=entry.get("importance", 5),
            markdown_path=entry.get("markdown_path"),
            checksum=entry.get("checksum"),
        )
        for tag in entry.get("tags", []):
            repo.add_memory_tag(entry["memory_id"], tag)

    conn = repo._conn
    assert conn is not None
    for scene in bundle.get("scenes", []):
        conn.execute(
            """
            INSERT INTO scenes (scene_id, campaign_id, location_slug, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (scene_id) DO UPDATE SET
                location_slug = excluded.location_slug,
                status        = excluded.status
            """,
            [
                scene["scene_id"],
                scene["campaign_id"],
                scene.get("location_slug"),
                scene.get("status", "active"),
            ],
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import a campaign JSON bundle")
    parser.add_argument("db_path", help="Path to target campaign.duckdb (will be created)")
    parser.add_argument("bundle_path", help="Path to JSON bundle file")
    args = parser.parse_args()

    _MIGRATIONS = (
        Path(__file__).parent.parent / "dungeon_daddy" / "data" / "migrations"
    )
    bundle = json.loads(Path(args.bundle_path).read_text(encoding="utf-8"))
    r = MemoryRepository(Path(args.db_path))
    r.initialize_schema(_MIGRATIONS)
    import_campaign_fixture(r, bundle)
    r.close()
    print("Import complete.")
