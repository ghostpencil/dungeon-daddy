from __future__ import annotations

from pathlib import Path

from dungeon_daddy.memory.markdown_store import compute_checksum, write_memory
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.sync import SyncReporter


def _write_valid_entry(path: Path, memory_id: str, campaign_id: str) -> str:
    fm = {
        "id": memory_id,
        "type": "event",
        "campaign_id": campaign_id,
        "updated_at": "2026-06-02T00:00:00Z",
    }
    write_memory(path, fm, "# Body")
    return compute_checksum(path)


class TestSyncReport:
    def test_clean_state_returns_no_issues(
        self, repo: MemoryRepository, tmp_path: Path
    ) -> None:
        memory_root = tmp_path / "memory"
        memory_root.mkdir()
        md_path = memory_root / "mem_001.md"
        checksum = _write_valid_entry(md_path, "mem_001", "camp_001")
        repo.save_memory_entry(
            "mem_001", "camp_001", "event", "Title",
            markdown_path=str(md_path), checksum=checksum,
        )
        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        assert issues == []

    def test_detects_missing_markdown_file(
        self, repo: MemoryRepository, tmp_path: Path
    ) -> None:
        memory_root = tmp_path / "memory"
        memory_root.mkdir()
        repo.save_memory_entry(
            "mem_001", "camp_001", "event", "Title",
            markdown_path=str(memory_root / "missing.md"),
            checksum="abc123",
        )
        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        kinds = [i.kind for i in issues]
        assert "missing_file" in kinds

    def test_detects_checksum_mismatch(
        self, repo: MemoryRepository, tmp_path: Path
    ) -> None:
        memory_root = tmp_path / "memory"
        memory_root.mkdir()
        md_path = memory_root / "mem_001.md"
        _write_valid_entry(md_path, "mem_001", "camp_001")
        repo.save_memory_entry(
            "mem_001", "camp_001", "event", "Title",
            markdown_path=str(md_path),
            checksum="stale_checksum",
        )
        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        kinds = [i.kind for i in issues]
        assert "checksum_mismatch" in kinds

    def test_detects_invalid_front_matter(
        self, repo: MemoryRepository, tmp_path: Path
    ) -> None:
        memory_root = tmp_path / "memory"
        memory_root.mkdir()
        md_path = memory_root / "mem_001.md"
        # Write file without required front matter fields
        write_memory(md_path, {"id": "mem_001"}, "# Body")
        checksum = compute_checksum(md_path)
        repo.save_memory_entry(
            "mem_001", "camp_001", "event", "Title",
            markdown_path=str(md_path), checksum=checksum,
        )
        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        kinds = [i.kind for i in issues]
        assert "invalid_front_matter" in kinds

    def test_detects_orphan_markdown_file(
        self, repo: MemoryRepository, tmp_path: Path
    ) -> None:
        memory_root = tmp_path / "memory"
        memory_root.mkdir()
        orphan = memory_root / "orphan.md"
        _write_valid_entry(orphan, "orphan_id", "camp_001")
        # No DB row for this file
        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        kinds = [i.kind for i in issues]
        assert "orphan_markdown" in kinds

    def test_detects_db_row_without_markdown_path(
        self, repo: MemoryRepository, tmp_path: Path
    ) -> None:
        memory_root = tmp_path / "memory"
        memory_root.mkdir()
        repo.save_memory_entry("mem_001", "camp_001", "event", "Title")
        # No markdown_path set — row has no linked file
        reporter = SyncReporter(repo, memory_root)
        issues = reporter.check()
        kinds = [i.kind for i in issues]
        assert "no_markdown_path" in kinds
