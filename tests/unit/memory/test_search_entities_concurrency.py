"""Slice B4d (L5) — `search_entities` is safe to call from the worker thread.

The narrator tool loop runs DuckDB reads from the per-view worker thread while
the main thread may touch the shared connection. Spec §10 L5: guard tool
queries with a repo-owned lock and run them on a cursor. This test drives many
concurrent `search_entities` calls and asserts every one returns the full,
correct result set with no exception.
"""
from __future__ import annotations

import threading
from pathlib import Path

from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "dungeon_daddy" / "data" / "migrations"
)


def test_concurrent_search_entities_is_safe(tmp_path: Path) -> None:
    repo = MemoryRepository(db_path=tmp_path / "t.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    for i in range(10):
        repo.save_actor(f"a{i}", "camp-A", "npc", f"mira-{i}", f"Mira {i}", tags=["theme:x"])

    n_threads = 8
    counts: list[int] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(n_threads)

    def worker() -> None:
        try:
            barrier.wait()
            for _ in range(25):
                rows = repo.search_entities("camp-A", tags=["theme:x"], limit=20)
                counts.append(len(rows))
        except Exception as exc:  # noqa: BLE001 — collected for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert counts and all(n == 10 for n in counts)
