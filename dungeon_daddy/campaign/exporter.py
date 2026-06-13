"""Export a live campaign DB to a CampaignManifest."""
from __future__ import annotations

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.memory.repository import MemoryRepository


def export_campaign_manifest(campaign_id: str, repo: MemoryRepository) -> CampaignManifest:
    """Reconstruct a CampaignManifest from a live campaign DB."""
    campaign = repo.get_campaign(campaign_id)
    if campaign is None:
        raise ValueError(f"Campaign not found: {campaign_id}")

    actors = _export_actors(campaign_id, repo)
    clocks = _export_clocks(campaign_id, repo)
    memory_seeds = _export_memory_seeds(campaign_id, repo)
    player_side = [a.slug for a in actors if a.actor_type == "pc"]

    return CampaignManifest(
        slug=campaign["slug"],
        title=campaign["title"],
        dungeon_slug=campaign.get("dungeon_slug") or campaign["slug"],
        world_actors=actors,
        factions=[],
        clocks=clocks,
        memory_seeds=memory_seeds,
        player_side=player_side,
    )


def _export_memory_seeds(campaign_id: str, repo: MemoryRepository) -> list[str]:
    rows = repo.get_memory_entries_by_campaign(campaign_id)
    return [r["summary"] for r in rows if r["status"] == "approved"]


def _slug_from_id(record_id: str, campaign_slug: str, prefix: str) -> str:
    """Extract slug portion from a prefixed ID like 'clock:campaign:slug'."""
    expected_prefix = f"{prefix}:{campaign_slug}:"
    if record_id.startswith(expected_prefix):
        return record_id[len(expected_prefix):]
    # Fallback: use last segment
    return record_id.rsplit(":", 1)[-1]


def _export_clocks(campaign_id: str, repo: MemoryRepository) -> list[ClockManifest]:
    rows = repo.get_clocks(campaign_id)
    campaign_slug = campaign_id.split(":", 1)[-1] if ":" in campaign_id else campaign_id
    clocks = []
    for r in rows:
        slug = _slug_from_id(r["clock_id"], campaign_slug, "clock")
        clocks.append(
            ClockManifest(
                slug=slug,
                label=r["label"],
                segments=r["segments"],
                filled=r["filled"],
                status=r["status"],
                clock_level=r.get("clock_level", "dungeon"),
                category=r.get("category"),
                scope_room_id=r.get("scope_room_id"),
                action_tags=r.get("action_tags", []),
                visible_to_player=r.get("visible_to_player", True),
                stakes=r.get("stakes"),
                completion_effect=r.get("completion_effect"),
            )
        )
    return clocks


def _export_actors(campaign_id: str, repo: MemoryRepository) -> list[ActorManifest]:
    rows = repo.get_actors_by_campaign(campaign_id)
    actors = []
    for r in rows:
        actor_id = r["actor_id"]
        ratings_rows = repo.get_actor_action_ratings(actor_id)
        action_ratings = {rr["action_key"]: rr["rating"] for rr in ratings_rows}
        stress_tracks = repo.get_actor_stress_tracks(actor_id)
        actors.append(
            ActorManifest(
                slug=r["slug"],
                display_name=r["display_name"],
                actor_type=r["actor_type"],
                status=r["status"],
                action_ratings=action_ratings,
                stress_tracks=stress_tracks,
            )
        )
    return actors
