from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(db_path=tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()
