from __future__ import annotations

from dungeon_daddy.memory.curation import build_curation_report
from dungeon_daddy.memory.repository import MemoryRepository


class TestCountByStatus:
    def test_empty_campaign_returns_empty_dict(self, repo: MemoryRepository) -> None:
        result = repo.count_by_status("camp_001")
        assert result == {}

    def test_counts_entries_by_status(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("m1", "camp_001", "event", "Title 1", status="draft")
        repo.save_memory_entry("m2", "camp_001", "event", "Title 2", status="draft")
        repo.save_memory_entry("m3", "camp_001", "event", "Title 3", status="approved")

        result = repo.count_by_status("camp_001")

        assert result == {"draft": 2, "approved": 1}

    def test_only_statuses_with_entries_appear(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("m1", "camp_001", "event", "Title 1", status="approved")
        result = repo.count_by_status("camp_001")
        assert "draft" not in result
        assert result["approved"] == 1

    def test_scopes_to_campaign_id(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("m1", "camp_001", "event", "Title 1", status="draft")
        repo.save_memory_entry("m2", "camp_002", "event", "Title 2", status="approved")

        result = repo.count_by_status("camp_001")

        assert result == {"draft": 1}
        assert "approved" not in result


class TestBuildCurationReport:
    def test_returns_one_entry_per_campaign(self, repo: MemoryRepository) -> None:
        report = build_curation_report(repo, ["camp_001", "camp_002"])

        assert len(report) == 2
        campaign_ids = {entry["campaign_id"] for entry in report}
        assert campaign_ids == {"camp_001", "camp_002"}

    def test_counts_reflect_actual_statuses(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry("m1", "camp_001", "event", "T1", status="draft")
        repo.save_memory_entry("m2", "camp_001", "event", "T2", status="draft")
        repo.save_memory_entry("m3", "camp_001", "event", "T3", status="approved")

        report = build_curation_report(repo, ["camp_001"])

        entry = report[0]
        assert entry["counts"] == {"draft": 2, "approved": 1}

    def test_drafts_contains_only_draft_entries(self, repo: MemoryRepository) -> None:
        repo.save_memory_entry(
            "m1", "camp_001", "event", "Draft Title", summary="A draft", importance=7, status="draft"
        )
        repo.save_memory_entry(
            "m2", "camp_001", "event", "Approved Title", summary="Approved", importance=5, status="approved"
        )

        report = build_curation_report(repo, ["camp_001"])
        drafts = report[0]["drafts"]

        assert len(drafts) == 1
        d = drafts[0]
        assert d["memory_id"] == "m1"
        assert d["title"] == "Draft Title"
        assert d["summary"] == "A draft"
        assert d["importance"] == 7
