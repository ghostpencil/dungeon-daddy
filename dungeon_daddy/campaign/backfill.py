"""Self-healing exit backfill for campaigns saved before Phase 48.

Pre-Phase-48 saves have an empty ``room_exits`` table, so the Play-mode EXITS
panel is blank. When such a save is loaded we derive its exits from the on-disk
``dungeon.json`` (the same logic the publish seeder uses) — but only when the
table is empty, so already-populated campaigns are never disturbed. This lets
old saves self-heal without running ``tools.backfill_room_exits`` by hand.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.seeder import (
    _default_label,
    _exit_id,
    _exit_type_for,
    seed_from_manifest,
)
from dungeon_daddy.data.models import Dungeon
from dungeon_daddy.memory.repository import MemoryRepository

_log = logging.getLogger(__name__)


def backfill_exits_if_empty(repo: MemoryRepository, dungeon_path: Path) -> int:
    """Derive ``room_exits`` from ``dungeon_path`` when the campaign has none.

    Returns the number of exits created — ``0`` if the campaign already has
    exits, the dungeon file is missing, or there is no campaign row. Never
    raises: a failed backfill must not block loading the save.
    """
    try:
        row = repo._conn.execute(
            "SELECT campaign_id, slug, title FROM campaigns LIMIT 1"
        ).fetchone()
        if row is None:
            return 0
        campaign_id, slug, title = row

        existing = repo._conn.execute(
            "SELECT count(*) FROM room_exits WHERE campaign_id = ?", [campaign_id]
        ).fetchone()[0]
        if existing > 0:
            return 0

        if not dungeon_path.exists():
            return 0

        dungeon = Dungeon.model_validate(
            json.loads(dungeon_path.read_text(encoding="utf-8"))
        )
        manifest = CampaignManifest(slug=slug, title=title, dungeon_slug=slug)
        result = seed_from_manifest(manifest, repo, campaign_id, dungeon=dungeon)
        if result.created:
            _log.info(
                "Backfilled %d room_exits on load for %s", result.created, campaign_id
            )
        return result.created
    except Exception as exc:  # never block loading a save
        _log.warning("Exit backfill on load skipped: %s", exc)
        return 0


def refresh_exit_labels(repo: MemoryRepository, dungeon_path: Path) -> int:
    """Re-derive each existing exit's ``label``/``exit_type`` from ``dungeon_path``.

    Corrects stale cosmetic labels on already-populated saves (e.g. ones seeded
    before the exit-type fix). Updates **only** ``label``/``exit_type`` — never
    ``status`` or any other column, so runtime exit state (discovered, unlocked,
    sealed, blocked) is preserved. Existing rows only; never creates exits (that
    is ``backfill_exits_if_empty``'s job). Returns the number of exits changed.
    Never raises: a failed refresh must not block loading the save.
    """
    try:
        row = repo._conn.execute(
            "SELECT campaign_id, slug FROM campaigns LIMIT 1"
        ).fetchone()
        if row is None:
            return 0
        campaign_id, slug = row

        if not dungeon_path.exists():
            return 0

        dungeon = Dungeon.model_validate(
            json.loads(dungeon_path.read_text(encoding="utf-8"))
        )

        updated = 0
        for level in dungeon.levels:
            for conn in level.connections:
                for from_room, to_room in [
                    (conn.from_room, conn.to_room),
                    (conn.to_room, conn.from_room),
                ]:
                    exit_id = _exit_id(slug, from_room, to_room)
                    existing = repo.get_exit_by_id(exit_id)
                    if existing is None:
                        continue
                    exit_type = _exit_type_for(conn.type)
                    label = _default_label(exit_type)
                    if existing["label"] != label or existing["exit_type"] != exit_type:
                        repo.update_exit_label(exit_id, label, exit_type)
                        updated += 1
        if updated:
            _log.info(
                "Refreshed %d exit label(s) on load for %s", updated, campaign_id
            )
        return updated
    except Exception as exc:  # never block loading a save
        _log.warning("Exit label refresh on load skipped: %s", exc)
        return 0
