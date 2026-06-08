from __future__ import annotations

from dungeon_daddy.memory.repository import MemoryRepository


def build_curation_report(
    repo: MemoryRepository, campaign_ids: list[str]
) -> list[dict]:
    report = []
    for campaign_id in campaign_ids:
        counts = repo.count_by_status(campaign_id)
        entries = repo.get_memory_entries_by_campaign(campaign_id)
        drafts = [
            {
                "memory_id": e["memory_id"],
                "title": e["title"],
                "summary": e["summary"],
                "importance": e["importance"],
            }
            for e in entries
            if e["status"] == "draft"
        ]
        report.append(
            {"campaign_id": campaign_id, "counts": counts, "drafts": drafts}
        )
    return report
