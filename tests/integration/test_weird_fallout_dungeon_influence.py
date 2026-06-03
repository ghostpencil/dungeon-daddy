from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import pytest

from dungeon_daddy.memory.markdown_store import read_memory, write_fallout_markdown
from dungeon_daddy.rpg.models import FalloutRecord


def _weird_fallout() -> FalloutRecord:
    return FalloutRecord(
        fallout_id="fo_weird_001",
        campaign_id="camp_1",
        actor_id="pc_mara",
        track_key="weird",
        severity="moderate",
        title="Marked",
        summary="The dungeon knows your shape.",
        mechanical_hooks={"dungeon_influence": True, "write_memory": True},
    )


def test_weird_fallout_writes_markdown_with_correct_front_matter(
    tmp_path: Path,
) -> None:
    fallout = _weird_fallout()
    md_path = write_fallout_markdown(fallout, tmp_path)
    assert md_path.exists()
    fm, _ = read_memory(md_path)
    assert fm["id"] == "fo_weird_001"
    assert fm["type"] == "fallout"
    assert fm["campaign_id"] == "camp_1"
    assert "updated_at" in fm


def test_weird_fallout_markdown_contains_track_and_fallout_tags(
    tmp_path: Path,
) -> None:
    fallout = _weird_fallout()
    md_path = write_fallout_markdown(fallout, tmp_path)
    fm, _ = read_memory(md_path)
    tags = fm.get("tags", [])
    assert "track:weird" in tags
    assert "fallout:active" in tags
