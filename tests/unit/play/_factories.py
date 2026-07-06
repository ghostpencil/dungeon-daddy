"""Shared helpers for play-package unit tests.

Mirrors ``tests/unit/rpg/_factories.py``: an importable module for the
duplicated migrations path and the default PC factory used across the
play-coordinator test modules (Phase 51.7 Slice 4 review follow-up).
"""
from __future__ import annotations

from pathlib import Path

from dungeon_daddy.rpg.models import ActorState

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


def make_actor(**kw: object) -> ActorState:
    """Default active PC (``pc-1``/Elara); override any field via ``kw``."""
    defaults: dict[str, object] = dict(
        actor_id="pc-1", campaign_id="camp-1", actor_type="pc",
        slug="elara", display_name="Elara", status="active",
        actions={"fight": 2, "sense": 1}, playbook_slug="fighter",
    )
    defaults.update(kw)
    return ActorState(**defaults)
