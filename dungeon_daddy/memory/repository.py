from __future__ import annotations

import json
from pathlib import Path

import duckdb

from dungeon_daddy.memory.models import DomainEvent
from dungeon_daddy.rpg.models import FactionState, FalloutRecord, Item, RoomObject


def _ensure_migration_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            name       TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _apply_migrations(conn: duckdb.DuckDBPyConnection, migrations_dir: Path) -> list[str]:
    _ensure_migration_table(conn)
    applied: set[str] = {
        row[0] for row in conn.execute("SELECT name FROM schema_migration").fetchall()
    }
    newly_applied: list[str] = []
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        if sql_file.name in applied:
            continue
        sql = sql_file.read_text(encoding="utf-8")
        # Execute each statement individually to handle multi-statement files
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_migration (name) VALUES (?)", [sql_file.name]
        )
        newly_applied.append(sql_file.name)
    return newly_applied


class MigrationRunner:
    """Standalone migration runner — opens and closes its own connection."""

    def __init__(self, migrations_dir: Path, db_path: Path) -> None:
        self._migrations_dir = migrations_dir
        self._db_path = db_path

    def sql_files(self) -> list[Path]:
        return sorted(self._migrations_dir.glob("*.sql"))

    def run(self) -> list[str]:
        conn = duckdb.connect(str(self._db_path))
        try:
            return _apply_migrations(conn, self._migrations_dir)
        finally:
            conn.close()


class MemoryRepository:
    """Persistent DuckDB repository for memory and domain events."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: duckdb.DuckDBPyConnection | None = duckdb.connect(str(db_path))

    def health_check(self) -> bool:
        if self._conn is None:
            return False
        try:
            self._conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def initialize_schema(self, migrations_dir: Path) -> None:
        assert self._conn is not None
        _apply_migrations(self._conn, migrations_dir)

    def list_tables(self) -> list[str]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        return [row[0] for row in rows]

    def insert_domain_event(self, event: DomainEvent) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO domain_events (event_id, campaign_id, event_type, payload, occurred_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                event.event_id,
                event.campaign_id,
                event.event_type,
                json.dumps(event.payload),
                event.occurred_at,
            ],
        )

    def get_domain_events(self, campaign_id: str) -> list[DomainEvent]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT event_id, campaign_id, event_type, payload, occurred_at
            FROM domain_events
            WHERE campaign_id = ?
            ORDER BY occurred_at
            """,
            [campaign_id],
        ).fetchall()
        return [
            DomainEvent(
                event_id=row[0],
                campaign_id=row[1],
                event_type=row[2],
                payload=json.loads(row[3]),
                occurred_at=row[4],
            )
            for row in rows
        ]

    def list_migrations(self) -> list[str]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT name FROM schema_migration ORDER BY applied_at"
        ).fetchall()
        return [row[0] for row in rows]

    # ------------------------------------------------------------------
    # Actors
    # ------------------------------------------------------------------

    def save_actor(
        self,
        actor_id: str,
        campaign_id: str,
        actor_type: str,
        slug: str,
        display_name: str,
        status: str = "active",
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO actors (actor_id, campaign_id, actor_type, slug, display_name, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (actor_id) DO UPDATE SET
                actor_type   = excluded.actor_type,
                slug         = excluded.slug,
                display_name = excluded.display_name,
                status       = excluded.status
            """,
            [actor_id, campaign_id, actor_type, slug, display_name, status],
        )

    def get_actor(self, actor_id: str) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT actor_id, campaign_id, actor_type, slug, display_name, status
            FROM actors WHERE actor_id = ?
            """,
            [actor_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "actor_id": row[0],
            "campaign_id": row[1],
            "actor_type": row[2],
            "slug": row[3],
            "display_name": row[4],
            "status": row[5],
        }

    def get_actors_by_campaign(self, campaign_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT actor_id, campaign_id, actor_type, slug, display_name, status
            FROM actors WHERE campaign_id = ?
            """,
            [campaign_id],
        ).fetchall()
        return [
            {
                "actor_id": row[0],
                "campaign_id": row[1],
                "actor_type": row[2],
                "slug": row[3],
                "display_name": row[4],
                "status": row[5],
            }
            for row in rows
        ]

    def save_actor_stress_track(
        self, actor_id: str, track_key: str, capacity: int, filled: int
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO stress_tracks (actor_id, track_key, capacity, filled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (actor_id, track_key) DO UPDATE SET
                capacity = excluded.capacity,
                filled   = excluded.filled
            """,
            [actor_id, track_key, capacity, filled],
        )

    def get_actor_stress_tracks(self, actor_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT track_key, capacity, filled FROM stress_tracks WHERE actor_id = ?",
            [actor_id],
        ).fetchall()
        return [{"track_key": r[0], "capacity": r[1], "filled": r[2]} for r in rows]

    def save_actor_action_rating(
        self, actor_id: str, action_key: str, rating: int
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO action_ratings (actor_id, action_key, rating)
            VALUES (?, ?, ?)
            ON CONFLICT (actor_id, action_key) DO UPDATE SET rating = excluded.rating
            """,
            [actor_id, action_key, rating],
        )

    def get_actor_action_ratings(self, actor_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT action_key, rating FROM action_ratings WHERE actor_id = ?",
            [actor_id],
        ).fetchall()
        return [{"action_key": r[0], "rating": r[1]} for r in rows]

    # ------------------------------------------------------------------
    # Memory entries
    # ------------------------------------------------------------------

    def save_memory_entry(
        self,
        memory_id: str,
        campaign_id: str,
        entry_type: str,
        title: str,
        summary: str = "",
        status: str = "draft",
        importance: int = 5,
        markdown_path: str | None = None,
        checksum: str | None = None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO memory_entries
                (memory_id, campaign_id, type, title, summary, status, importance,
                 markdown_path, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (memory_id) DO UPDATE SET
                type          = excluded.type,
                title         = excluded.title,
                summary       = excluded.summary,
                status        = excluded.status,
                importance    = excluded.importance,
                markdown_path = excluded.markdown_path,
                checksum      = excluded.checksum
            """,
            [
                memory_id, campaign_id, entry_type, title, summary,
                status, importance, markdown_path, checksum,
            ],
        )

    def get_memory_entry(self, memory_id: str) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT memory_id, campaign_id, type, title, summary, status,
                   importance, markdown_path, checksum
            FROM memory_entries WHERE memory_id = ?
            """,
            [memory_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "memory_id": row[0],
            "campaign_id": row[1],
            "type": row[2],
            "title": row[3],
            "summary": row[4],
            "status": row[5],
            "importance": row[6],
            "markdown_path": row[7],
            "checksum": row[8],
        }

    def add_memory_tag(self, memory_id: str, tag: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)
            ON CONFLICT (memory_id, tag) DO NOTHING
            """,
            [memory_id, tag],
        )

    def get_memory_tags(self, memory_id: str) -> list[str]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT tag FROM memory_tags WHERE memory_id = ?", [memory_id]
        ).fetchall()
        return [r[0] for r in rows]

    def add_memory_link(self, from_id: str, to_id: str, link_type: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO memory_links (from_id, to_id, link_type) VALUES (?, ?, ?)
            ON CONFLICT (from_id, to_id, link_type) DO NOTHING
            """,
            [from_id, to_id, link_type],
        )

    def get_memory_links(self, from_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT from_id, to_id, link_type FROM memory_links WHERE from_id = ?",
            [from_id],
        ).fetchall()
        return [{"from_id": r[0], "to_id": r[1], "link_type": r[2]} for r in rows]

    def count_by_status(self, campaign_id: str) -> dict[str, int]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT status, COUNT(*) FROM memory_entries
            WHERE campaign_id = ?
            GROUP BY status
            """,
            [campaign_id],
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def update_memory_status(self, memory_id: str, status: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE memory_entries SET status = ? WHERE memory_id = ?",
            [status, memory_id],
        )

    def update_memory_checksum(
        self, memory_id: str, checksum: str, markdown_path: str
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE memory_entries SET checksum = ?, markdown_path = ?
            WHERE memory_id = ?
            """,
            [checksum, markdown_path, memory_id],
        )

    def get_memory_entries_by_campaign_all(self) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT memory_id, campaign_id, type, title, summary, status,
                   importance, markdown_path, checksum
            FROM memory_entries
            ORDER BY importance DESC
            """
        ).fetchall()
        return [
            {
                "memory_id": r[0],
                "campaign_id": r[1],
                "type": r[2],
                "title": r[3],
                "summary": r[4],
                "status": r[5],
                "importance": r[6],
                "markdown_path": r[7],
                "checksum": r[8],
            }
            for r in rows
        ]

    def get_memory_entries_by_campaign(self, campaign_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT memory_id, campaign_id, type, title, summary, status,
                   importance, markdown_path, checksum
            FROM memory_entries WHERE campaign_id = ?
            ORDER BY importance DESC
            """,
            [campaign_id],
        ).fetchall()
        return [
            {
                "memory_id": r[0],
                "campaign_id": r[1],
                "type": r[2],
                "title": r[3],
                "summary": r[4],
                "status": r[5],
                "importance": r[6],
                "markdown_path": r[7],
                "checksum": r[8],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Action resolutions
    # ------------------------------------------------------------------

    def save_action_resolution(
        self,
        resolution_id: str,
        campaign_id: str,
        actor_id: str,
        action_key: str,
        outcome: str,
        scene_id: str | None = None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO action_resolutions
                (resolution_id, campaign_id, scene_id, actor_id, action_key, outcome)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (resolution_id) DO UPDATE SET
                outcome    = excluded.outcome,
                action_key = excluded.action_key
            """,
            [resolution_id, campaign_id, scene_id, actor_id, action_key, outcome],
        )

    def get_action_resolutions(self, campaign_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT resolution_id, campaign_id, scene_id, actor_id, action_key, outcome
            FROM action_resolutions WHERE campaign_id = ?
            ORDER BY resolved_at
            """,
            [campaign_id],
        ).fetchall()
        return [
            {
                "resolution_id": r[0],
                "campaign_id": r[1],
                "scene_id": r[2],
                "actor_id": r[3],
                "action_key": r[4],
                "outcome": r[5],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Clocks
    # ------------------------------------------------------------------

    def save_clock(
        self,
        clock_id: str,
        campaign_id: str,
        label: str,
        segments: int,
        filled: int = 0,
        status: str = "active",
        scope_room_id: str | None = None,
        action_tags: list[str] | None = None,
        clock_level: str = "dungeon",
        category: str | None = None,
        level_id: str | None = None,
        owner_actor_id: str | None = None,
        stakes: str | None = None,
        completion_effect: str | None = None,
        visible_to_player: bool = True,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO clocks (
                clock_id, campaign_id, label, segments, filled, status,
                scope_room_id, action_tags,
                clock_level, category, level_id, owner_actor_id,
                stakes, completion_effect, visible_to_player
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (clock_id) DO UPDATE SET
                label             = excluded.label,
                segments          = excluded.segments,
                filled            = excluded.filled,
                status            = excluded.status,
                scope_room_id     = excluded.scope_room_id,
                action_tags       = excluded.action_tags,
                clock_level       = excluded.clock_level,
                category          = excluded.category,
                level_id          = excluded.level_id,
                owner_actor_id    = excluded.owner_actor_id,
                stakes            = excluded.stakes,
                completion_effect = excluded.completion_effect,
                visible_to_player = excluded.visible_to_player
            """,
            [clock_id, campaign_id, label, segments, filled, status,
             scope_room_id, json.dumps(action_tags or []),
             clock_level, category, level_id, owner_actor_id,
             stakes, completion_effect, visible_to_player],
        )

    def delete_clock(self, clock_id: str) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM clocks WHERE clock_id = ?", [clock_id])

    def update_clock_progress(
        self,
        clock_id: str,
        filled: int,
        status: str,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE clocks SET filled = ?, status = ? WHERE clock_id = ?",
            [filled, status, clock_id],
        )

    def update_clock_scope(
        self,
        clock_id: str,
        scope_room_id: str | None,
        action_tags: list[str],
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            UPDATE clocks SET scope_room_id = ?, action_tags = ?
            WHERE clock_id = ?
            """,
            [scope_room_id, json.dumps(action_tags), clock_id],
        )

    def get_clocks(self, campaign_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT clock_id, campaign_id, label, segments, filled, status,
                   scope_room_id, action_tags,
                   clock_level, category, level_id, owner_actor_id,
                   stakes, completion_effect, visible_to_player
            FROM clocks WHERE campaign_id = ?
            """,
            [campaign_id],
        ).fetchall()
        return [
            {
                "clock_id": r[0],
                "campaign_id": r[1],
                "label": r[2],
                "segments": r[3],
                "filled": r[4],
                "status": r[5],
                "scope_room_id": r[6],
                "action_tags": json.loads(r[7]) if r[7] else [],
                "clock_level": r[8] if r[8] else "dungeon",
                "category": r[9],
                "level_id": r[10],
                "owner_actor_id": r[11],
                "stakes": r[12],
                "completion_effect": r[13],
                "visible_to_player": bool(r[14]) if r[14] is not None else True,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def save_session(
        self,
        session_id: str,
        campaign_id: str,
        session_number: int,
        notes: str | None = None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO sessions (session_id, campaign_id, session_number, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (session_id) DO UPDATE SET
                session_number = excluded.session_number,
                notes          = excluded.notes
            """,
            [session_id, campaign_id, session_number, notes],
        )

    def get_session(self, session_id: str) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT session_id, campaign_id, session_number, notes FROM sessions WHERE session_id = ?",
            [session_id],
        ).fetchone()
        if row is None:
            return None
        return {"session_id": row[0], "campaign_id": row[1], "session_number": row[2], "notes": row[3]}

    # ------------------------------------------------------------------
    # Scenes
    # ------------------------------------------------------------------

    def save_scene(
        self,
        scene_id: str,
        campaign_id: str,
        location_slug: str | None = None,
        session_id: str | None = None,
        status: str = "active",
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO scenes (scene_id, campaign_id, session_id, location_slug, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (scene_id) DO UPDATE SET
                location_slug = excluded.location_slug,
                status        = excluded.status
            """,
            [scene_id, campaign_id, session_id, location_slug, status],
        )

    def get_scene(self, scene_id: str) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT scene_id, campaign_id, session_id, location_slug, status FROM scenes WHERE scene_id = ?",
            [scene_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "scene_id": row[0],
            "campaign_id": row[1],
            "session_id": row[2],
            "location_slug": row[3],
            "status": row[4],
        }

    # ------------------------------------------------------------------
    # Campaign
    # ------------------------------------------------------------------

    def save_campaign(
        self,
        campaign_id: str,
        slug: str,
        title: str,
        status: str = "active",
        dungeon_slug: str | None = None,
    ) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO campaigns (campaign_id, slug, title, status, dungeon_slug)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (campaign_id) DO UPDATE SET
                slug         = excluded.slug,
                title        = excluded.title,
                status       = excluded.status,
                dungeon_slug = excluded.dungeon_slug
            """,
            [campaign_id, slug, title, status, dungeon_slug],
        )

    def get_campaign(self, campaign_id: str) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT campaign_id, slug, title, status, dungeon_slug
            FROM campaigns WHERE campaign_id = ?
            """,
            [campaign_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "campaign_id": row[0],
            "slug": row[1],
            "title": row[2],
            "status": row[3],
            "dungeon_slug": row[4],
        }

    # ------------------------------------------------------------------
    # Fallout
    # ------------------------------------------------------------------

    def save_fallout_record(self, fallout: FalloutRecord) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO fallout
                (fallout_id, campaign_id, actor_id, track_key, severity,
                 title, summary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (fallout_id) DO UPDATE SET
                track_key = excluded.track_key,
                severity  = excluded.severity,
                title     = excluded.title,
                summary   = excluded.summary,
                status    = excluded.status
            """,
            [
                fallout.fallout_id,
                fallout.campaign_id,
                fallout.actor_id,
                fallout.track_key,
                fallout.severity,
                fallout.title,
                fallout.summary,
                fallout.status,
            ],
        )

    def get_fallout_records(
        self, campaign_id: str, actor_id: str
    ) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT fallout_id, campaign_id, actor_id, track_key, severity,
                   title, summary, status
            FROM fallout
            WHERE campaign_id = ? AND actor_id = ?
            ORDER BY fallout_id
            """,
            [campaign_id, actor_id],
        ).fetchall()
        return [
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
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Factions
    # ------------------------------------------------------------------

    _REPUTATION_TIERS: list[str] = ["hostile", "cold", "neutral", "warm", "allied"]

    def save_faction(self, faction: FactionState) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO factions (
                faction_id, campaign_id, slug, display_name,
                concept, goal, status, reputation, tier, tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (faction_id) DO UPDATE SET
                slug         = excluded.slug,
                display_name = excluded.display_name,
                concept      = excluded.concept,
                goal         = excluded.goal,
                status       = excluded.status,
                reputation   = excluded.reputation,
                tier         = excluded.tier,
                tags         = excluded.tags
            """,
            [
                faction.faction_id,
                faction.campaign_id,
                faction.slug,
                faction.display_name,
                faction.concept,
                faction.goal,
                faction.status,
                faction.reputation,
                faction.tier,
                json.dumps(faction.tags),
            ],
        )

    def get_factions(self, campaign_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT faction_id, campaign_id, slug, display_name,
                   concept, goal, status, reputation, tier, tags
            FROM factions WHERE campaign_id = ?
            ORDER BY display_name
            """,
            [campaign_id],
        ).fetchall()
        return [
            {
                "faction_id": r[0],
                "campaign_id": r[1],
                "slug": r[2],
                "display_name": r[3],
                "concept": r[4],
                "goal": r[5],
                "status": r[6],
                "reputation": r[7],
                "tier": r[8],
                "tags": json.loads(r[9]) if r[9] else [],
            }
            for r in rows
        ]

    def update_faction_reputation(self, faction_id: str, delta_steps: int) -> str:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT reputation FROM factions WHERE faction_id = ?",
            [faction_id],
        ).fetchone()
        if row is None:
            raise ValueError(f"Faction {faction_id!r} not found")
        current = row[0]
        tiers = self._REPUTATION_TIERS
        idx = tiers.index(current)
        new_idx = max(0, min(len(tiers) - 1, idx + delta_steps))
        new_rep = tiers[new_idx]
        self._conn.execute(
            "UPDATE factions SET reputation = ? WHERE faction_id = ?",
            [new_rep, faction_id],
        )
        return new_rep

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def save_item(self, item: Item) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO items (
                item_id, campaign_id, slug, display_name, item_type,
                description, owner_actor_id, level_id, status,
                charges_current, charges_max, is_equipped
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (item_id) DO UPDATE SET
                slug            = excluded.slug,
                display_name    = excluded.display_name,
                item_type       = excluded.item_type,
                description     = excluded.description,
                owner_actor_id  = excluded.owner_actor_id,
                level_id        = excluded.level_id,
                status          = excluded.status,
                charges_current = excluded.charges_current,
                charges_max     = excluded.charges_max,
                is_equipped     = excluded.is_equipped
            """,
            [
                item.item_id,
                item.campaign_id,
                item.slug,
                item.display_name,
                item.item_type,
                item.description,
                item.owner_actor_id,
                item.level_id,
                item.status,
                item.charges_current,
                item.charges_max,
                item.is_equipped,
            ],
        )
        self._conn.execute(
            "DELETE FROM item_features WHERE item_id = ?", [item.item_id]
        )
        for f in item.features:
            self._conn.execute(
                """
                INSERT INTO item_features (feature_id, item_id, feature_type, action_key, modifier)
                VALUES (?, ?, ?, ?, ?)
                """,
                [f.feature_id, f.item_id, f.feature_type, f.action_key, f.modifier],
            )

    def get_items(self, campaign_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT item_id, campaign_id, slug, display_name, item_type,
                   description, owner_actor_id, level_id, status,
                   charges_current, charges_max, is_equipped
            FROM items WHERE campaign_id = ?
            ORDER BY display_name
            """,
            [campaign_id],
        ).fetchall()
        return [self._item_row_to_dict(r) for r in rows]

    def get_items_by_actor(self, actor_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT item_id, campaign_id, slug, display_name, item_type,
                   description, owner_actor_id, level_id, status,
                   charges_current, charges_max, is_equipped
            FROM items WHERE owner_actor_id = ?
            ORDER BY display_name
            """,
            [actor_id],
        ).fetchall()
        return [self._item_row_to_dict(r) for r in rows]

    def _item_row_to_dict(self, r: tuple) -> dict:
        assert self._conn is not None
        item_id = r[0]
        feature_rows = self._conn.execute(
            """
            SELECT feature_id, item_id, feature_type, action_key, modifier
            FROM item_features WHERE item_id = ?
            ORDER BY feature_id
            """,
            [item_id],
        ).fetchall()
        features = [
            {
                "feature_id": fr[0],
                "item_id": fr[1],
                "feature_type": fr[2],
                "action_key": fr[3],
                "modifier": fr[4],
            }
            for fr in feature_rows
        ]
        return {
            "item_id": r[0],
            "campaign_id": r[1],
            "slug": r[2],
            "display_name": r[3],
            "item_type": r[4],
            "description": r[5],
            "owner_actor_id": r[6],
            "level_id": r[7],
            "status": r[8],
            "charges_current": r[9],
            "charges_max": r[10],
            "is_equipped": r[11],
            "features": features,
        }

    def update_item_status(self, item_id: str, status: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE items SET status = ? WHERE item_id = ?", [status, item_id]
        )

    def update_item_charges(self, item_id: str, charges_current: int) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE items SET charges_current = ? WHERE item_id = ?",
            [charges_current, item_id],
        )

    def update_item_equipped(self, item_id: str, is_equipped: bool) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE items SET is_equipped = ? WHERE item_id = ?",
            [is_equipped, item_id],
        )

    def update_item_owner(self, item_id: str, owner_actor_id: str | None) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE items SET owner_actor_id = ? WHERE item_id = ?",
            [owner_actor_id, item_id],
        )

    def update_item_slug(self, item_id: str, new_slug: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE items SET slug = ? WHERE item_id = ?",
            [new_slug, item_id],
        )

    # ------------------------------------------------------------------
    # Room Objects
    # ------------------------------------------------------------------

    def save_room_object(self, obj: RoomObject) -> None:
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT INTO room_objects (
                object_id, campaign_id, room_id, level_id, slug,
                display_name, archetype, description, current_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (object_id) DO UPDATE SET
                room_id      = excluded.room_id,
                level_id     = excluded.level_id,
                slug         = excluded.slug,
                display_name = excluded.display_name,
                archetype    = excluded.archetype,
                description  = excluded.description,
                current_state = excluded.current_state
            """,
            [
                obj.object_id,
                obj.campaign_id,
                obj.room_id,
                obj.level_id,
                obj.slug,
                obj.display_name,
                obj.archetype,
                obj.description,
                obj.current_state,
            ],
        )
        self._conn.execute(
            "DELETE FROM object_transitions WHERE object_id = ?", [obj.object_id]
        )
        for t in obj.transitions:
            self._conn.execute(
                """
                INSERT INTO object_transitions (
                    transition_id, object_id, from_state, to_state,
                    trigger, requires_item_slug, spawns_item_slug, advances_clock_slug
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    t.transition_id,
                    t.object_id,
                    t.from_state,
                    t.to_state,
                    t.trigger,
                    t.requires_item_slug,
                    t.spawns_item_slug,
                    t.advances_clock_slug,
                ],
            )

    def get_room_object(self, object_id: str) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT object_id, campaign_id, room_id, level_id, slug,
                   display_name, archetype, description, current_state
            FROM room_objects WHERE object_id = ?
            """,
            [object_id],
        ).fetchone()
        if row is None:
            return None
        return self._room_object_row_to_dict(row)

    def get_objects_by_room(self, campaign_id: str, room_id: str) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT object_id, campaign_id, room_id, level_id, slug,
                   display_name, archetype, description, current_state
            FROM room_objects
            WHERE campaign_id = ? AND room_id = ?
            ORDER BY display_name
            """,
            [campaign_id, room_id],
        ).fetchall()
        return [self._room_object_row_to_dict(r) for r in rows]

    def update_object_state(self, object_id: str, new_state: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE room_objects SET current_state = ? WHERE object_id = ?",
            [new_state, object_id],
        )

    def _room_object_row_to_dict(self, r: tuple) -> dict:
        assert self._conn is not None
        object_id = r[0]
        t_rows = self._conn.execute(
            """
            SELECT transition_id, object_id, from_state, to_state,
                   trigger, requires_item_slug, spawns_item_slug, advances_clock_slug
            FROM object_transitions WHERE object_id = ?
            ORDER BY transition_id
            """,
            [object_id],
        ).fetchall()
        transitions = [
            {
                "transition_id": tr[0],
                "object_id": tr[1],
                "from_state": tr[2],
                "to_state": tr[3],
                "trigger": tr[4],
                "requires_item_slug": tr[5],
                "spawns_item_slug": tr[6],
                "advances_clock_slug": tr[7],
            }
            for tr in t_rows
        ]
        return {
            "object_id": r[0],
            "campaign_id": r[1],
            "room_id": r[2],
            "level_id": r[3],
            "slug": r[4],
            "display_name": r[5],
            "archetype": r[6],
            "description": r[7],
            "current_state": r[8],
            "transitions": transitions,
        }

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
