from __future__ import annotations

import uuid
from typing import Literal

from dungeon_daddy.memory.models import ContextBundle, MemoryEntry
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetriever
from dungeon_daddy.rpg.service import compute_effective_ratings


class ContextBundleBuilder:
    def __init__(
        self,
        campaign_id: str,
        scene_id: str | None,
        mode: Literal["run_scene", "recap", "room_revisit", "fallout_resolution"],
        focus_actor_ids: list[str],
        token_budget: int,
    ) -> None:
        self._campaign_id = campaign_id
        self._scene_id = scene_id
        self._mode = mode
        self._focus_actor_ids = focus_actor_ids
        self._token_budget = token_budget

    def build(self, repo: MemoryRepository) -> ContextBundle:
        memory_cards, must_remember, provenance = self._fetch_memories(repo)
        return ContextBundle(
            bundle_id=str(uuid.uuid4()),
            campaign_id=self._campaign_id,
            scene_id=self._scene_id,
            mode=self._mode,
            scene_brief=self._fetch_scene_brief(repo),
            mechanical_state=self._fetch_mechanical_state(repo),
            active_fallout=self._fetch_active_fallout(repo),
            open_clocks=self._fetch_open_clocks(repo),
            memory_cards=memory_cards,
            must_remember=must_remember,
            faction_reputations=self._fetch_faction_reputations(repo),
            inventory=self._fetch_inventory(repo),
            provenance=provenance,
        )

    def _fetch_memories(
        self, repo: MemoryRepository
    ) -> tuple[list[dict], list[str], dict]:
        retriever = MemoryRetriever(repo, self._campaign_id)
        all_entries = retriever.query()
        pinned = [e for e in all_entries if e.importance >= 9]
        regular = [e for e in all_entries if e.importance < 9]
        kept_regular, omitted = retriever.trim_to_budget(regular, self._token_budget)
        kept = pinned + kept_regular
        cards = [
            {
                "memory_id": e.memory_id,
                "title": e.title,
                "summary": e.summary,
                "importance": e.importance,
            }
            for e in kept
        ]
        must_remember = [e.memory_id for e in pinned]
        provenance = {
            "retrieved": len(all_entries),
            "omitted": omitted,
            "focus_actor_ids": self._focus_actor_ids,
        }
        return cards, must_remember, provenance

    def _fetch_open_clocks(self, repo: MemoryRepository) -> list[dict]:
        clocks = [c for c in repo.get_clocks(self._campaign_id) if c["status"] == "active"]
        for c in clocks:
            owner_id = c.get("owner_actor_id")
            if owner_id:
                actor = repo.get_actor(owner_id)
                c["owner_display_name"] = actor["display_name"] if actor else None
        return clocks

    def _fetch_active_fallout(self, repo: MemoryRepository) -> list[dict]:
        result: list[dict] = []
        for actor_id in self._focus_actor_ids:
            records = repo.get_fallout_records(self._campaign_id, actor_id)
            result.extend(r for r in records if r["status"] != "resolved")
        return result

    def _fetch_mechanical_state(self, repo: MemoryRepository) -> dict:
        state: dict = {}
        for actor_id in self._focus_actor_ids:
            state[actor_id] = {
                "action_ratings": repo.get_actor_action_ratings(actor_id),
                "stress_tracks": repo.get_actor_stress_tracks(actor_id),
            }
        return state

    def _fetch_faction_reputations(self, repo: MemoryRepository) -> list[dict]:
        factions = repo.get_factions(self._campaign_id)
        return [
            {
                "faction_id": f["faction_id"],
                "slug": f["slug"],
                "display_name": f["display_name"],
                "reputation": f["reputation"],
                "goal": f["goal"],
                "tier": f["tier"],
                "status": f["status"],
            }
            for f in factions
            if f["status"] == "active"
        ]

    def _fetch_inventory(self, repo: MemoryRepository) -> dict:
        result: dict = {}
        for actor_id in self._focus_actor_ids:
            items = repo.get_items_by_actor(actor_id)
            base_ratings = {
                r["action_key"]: r["rating"]
                for r in repo.get_actor_action_ratings(actor_id)
            }
            kits = [
                {
                    "slug": i["slug"],
                    "display_name": i["display_name"],
                    "charges_current": i["charges_current"],
                    "charges_max": i["charges_max"],
                }
                for i in items
                if i["item_type"] == "class_kit" and i["status"] == "active"
            ]
            dungeon_items = [
                {
                    "slug": i["slug"],
                    "display_name": i["display_name"],
                    "description": i["description"],
                    "status": i["status"],
                    "level_bound": i["level_id"] is not None,
                }
                for i in items
                if i["item_type"] == "dungeon_item"
            ]
            equipped = [
                {
                    "slug": i["slug"],
                    "display_name": i["display_name"],
                    "features": i.get("features", []),
                }
                for i in items
                if i["item_type"] == "equipped_gear" and i.get("is_equipped")
            ]
            result[actor_id] = {
                "kits": kits,
                "dungeon_items": dungeon_items,
                "equipped": equipped,
                "effective_actions": compute_effective_ratings(
                    actor_id, base_ratings, repo
                ),
            }
        return result

    def _fetch_scene_brief(self, repo: MemoryRepository) -> dict:
        if self._scene_id is None:
            return {}
        row = repo._conn.execute(
            "SELECT scene_id, location_slug, status FROM scenes WHERE scene_id = ?",
            [self._scene_id],
        ).fetchone()
        if row is None:
            return {}
        return {"scene_id": row[0], "location_slug": row[1], "status": row[2]}
