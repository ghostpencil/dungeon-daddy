from __future__ import annotations

import dataclasses
from pathlib import Path

from dungeon_daddy.memory.markdown_store import (
    compute_checksum,
    read_memory,
    validate_front_matter,
)
from dungeon_daddy.memory.repository import MemoryRepository


@dataclasses.dataclass
class SyncIssue:
    kind: str  # missing_file | checksum_mismatch | invalid_front_matter | orphan_markdown | no_markdown_path
    memory_id: str | None
    path: str | None
    detail: str = ""


class SyncReporter:
    def __init__(self, repo: MemoryRepository, memory_root: Path) -> None:
        self._repo = repo
        self._memory_root = memory_root

    def check(self) -> list[SyncIssue]:
        issues: list[SyncIssue] = []
        db_paths: set[str] = set()

        entries = self._repo.get_memory_entries_by_campaign_all()
        for entry in entries:
            memory_id = entry["memory_id"]
            md_path_str = entry["markdown_path"]

            if md_path_str is None:
                issues.append(
                    SyncIssue(
                        kind="no_markdown_path",
                        memory_id=memory_id,
                        path=None,
                        detail="DB row has no markdown_path",
                    )
                )
                continue

            db_paths.add(md_path_str)
            md_path = Path(md_path_str)

            if not md_path.exists():
                issues.append(
                    SyncIssue(
                        kind="missing_file",
                        memory_id=memory_id,
                        path=md_path_str,
                        detail="Markdown file not found on disk",
                    )
                )
                continue

            # Validate front matter
            try:
                front_matter, _ = read_memory(md_path)
                validate_front_matter(front_matter)
            except ValueError as exc:
                issues.append(
                    SyncIssue(
                        kind="invalid_front_matter",
                        memory_id=memory_id,
                        path=md_path_str,
                        detail=str(exc),
                    )
                )
                continue

            # Checksum check
            actual = compute_checksum(md_path)
            stored = entry["checksum"]
            if stored != actual:
                issues.append(
                    SyncIssue(
                        kind="checksum_mismatch",
                        memory_id=memory_id,
                        path=md_path_str,
                        detail=f"stored={stored!r} actual={actual!r}",
                    )
                )

        # Orphan Markdown files — .md files in tree not referenced by DB
        for md_file in self._memory_root.rglob("*.md"):
            if str(md_file) not in db_paths:
                issues.append(
                    SyncIssue(
                        kind="orphan_markdown",
                        memory_id=None,
                        path=str(md_file),
                        detail="Markdown file has no corresponding DB row",
                    )
                )

        return issues
