"""Slice B4d (L5) — `search_entities` is safe to call from the worker thread.

The narrator tool loop runs DuckDB reads from the per-view worker thread while
the main thread may touch the shared connection. Spec §10 L5: guard tool
queries with a repo-owned lock and run them on a dedicated cursor.

Two distinct properties, and they are held by two distinct mechanisms:

- worker vs **worker** — serialized by `_read_lock`.
- worker vs **main thread** — kept apart by `self._conn.cursor()` *only*. The
  main thread's repo calls never take `_read_lock`, so the lock cannot help
  here; the cursor is what does the work.

Both need their own test, or a mutation that deletes either one stays green
(the B4 review found exactly that: the lock was fully mutation-survivable).
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


def test_search_entities_does_not_interleave_with_main_thread_connection_use(
    tmp_path: Path,
) -> None:
    """The real L5 scenario: a worker looks things up *while* the main thread
    uses the shared connection.

    This is what `self._conn.cursor()` buys — `_read_lock` cannot help, because
    `save_actor`/`get_actors_by_campaign` never acquire it. Deleting the cursor
    must fail this test.
    """
    repo = MemoryRepository(db_path=tmp_path / "t.duckdb")
    repo.initialize_schema(MIGRATIONS_DIR)
    for i in range(10):
        repo.save_actor(f"a{i}", "camp-A", "npc", f"mira-{i}", f"Mira {i}", tags=["theme:x"])

    errors: list[Exception] = []
    wrong_counts: list[int] = []
    stop = threading.Event()
    started = threading.Barrier(5)  # 4 workers + the main thread

    def worker() -> None:
        try:
            started.wait()
            while not stop.is_set():
                rows = repo.search_entities("camp-A", tags=["theme:x"], limit=20)
                if len(rows) != 10:
                    wrong_counts.append(len(rows))
        except Exception as exc:  # noqa: BLE001 — collected for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    started.wait()
    try:
        # Main thread hammers the shared connection on an unrelated campaign,
        # so the workers' result set stays a constant 10 throughout.
        for i in range(150):
            repo.save_actor(f"m{i}", "camp-B", "npc", f"extra-{i}", f"Extra {i}")
            repo.get_actors_by_campaign("camp-B")
    finally:
        stop.set()
        for t in threads:
            t.join()

    assert errors == []
    assert wrong_counts == []
