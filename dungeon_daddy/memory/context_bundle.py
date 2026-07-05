from __future__ import annotations

import uuid
from typing import Any, Literal

from dungeon_daddy.memory.models import ContextBundle
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetriever
from dungeon_daddy.rpg.models import RoomObject
from dungeon_daddy.rpg.obstacles import obstacle_approach_verbs
from dungeon_daddy.rpg.service import compute_effective_ratings


class ContextBundleBuilder:
    def __init__(
        self,
        campaign_id: str,
        scene_id: str | None,
        mode: Literal["run_scene", "recap", "room_revisit", "fallout_resolution"],
        focus_actor_ids: list[str],
        token_budget: int,
        current_room_id: str | None = None,
    ) -> None:
        self._campaign_id = campaign_id
        self._scene_id = scene_id
        self._mode = mode
        self._focus_actor_ids = focus_actor_ids
        self._token_budget = token_budget
        self._current_room_id = current_room_id

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
            current_room=self._fetch_current_room(repo),
            provenance=provenance,
        )

    def _fetch_memories(
        self, repo: MemoryRepository
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
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

    def _fetch_open_clocks(self, repo: MemoryRepository) -> list[dict[str, Any]]:
        clocks = [c for c in repo.get_clocks(self._campaign_id) if c["status"] == "active"]
        for c in clocks:
            owner_id = c.get("owner_actor_id")
            if owner_id:
                actor = repo.get_actor(owner_id)
                c["owner_display_name"] = actor["display_name"] if actor else None
        return clocks

    def _fetch_active_fallout(self, repo: MemoryRepository) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for actor_id in self._focus_actor_ids:
            records = repo.get_fallout_records(self._campaign_id, actor_id)
            result.extend(r for r in records if r["status"] != "resolved")
        return result

    def _fetch_mechanical_state(self, repo: MemoryRepository) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for actor_id in self._focus_actor_ids:
            state[actor_id] = {
                "action_ratings": repo.get_actor_action_ratings(actor_id),
                "stress_tracks": repo.get_actor_stress_tracks(actor_id),
            }
        return state

    def _fetch_faction_reputations(self, repo: MemoryRepository) -> list[dict[str, Any]]:
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

    def _fetch_inventory(self, repo: MemoryRepository) -> dict[str, Any]:
        result: dict[str, Any] = {}
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

    def _fetch_current_room(self, repo: MemoryRepository) -> dict[str, Any]:
        if self._current_room_id is None:
            return {}
        return build_room_noun_context(repo, self._campaign_id, self._current_room_id)

    def _fetch_scene_brief(self, repo: MemoryRepository) -> dict[str, Any]:
        if self._scene_id is None:
            return {}
        assert repo._conn is not None
        row = repo._conn.execute(
            "SELECT scene_id, location_slug, status FROM scenes WHERE scene_id = ?",
            [self._scene_id],
        ).fetchone()
        if row is None:
            return {}
        return {"scene_id": row[0], "location_slug": row[1], "status": row[2]}


def _actor_noun(actor: dict[str, Any]) -> dict[str, Any]:
    return {
        "actor_id": actor["actor_id"],
        "slug": actor["slug"],
        "display_name": actor["display_name"],
        "status": actor["status"],
        # Carried so the overlay status chip and the dialogue gate (is_speakable)
        # can read a creature's stance toward the party (Phase 50.6 §5.2/§6).
        "disposition": actor.get("disposition", "neutral"),
    }


def build_room_noun_context(
    repo: MemoryRepository, campaign_id: str, room_id: str
) -> dict[str, Any]:
    """The enriched ``current_room`` block: the concrete targets in a room.

    Returns ``objects`` / ``loose_items`` / ``npcs`` / ``monsters`` / ``exits``
    (plus ``room_id``) — the shape the Phase 50 noun provider
    (:func:`dungeon_daddy.rpg.action_options.available_nouns`) reads. Shared by
    the context bundle's ``current_room`` block and the Play-mode VNA panel.
    """
    objects = repo.get_objects_by_room(campaign_id, room_id)
    raw_items = repo.get_items_by_room(campaign_id, room_id)
    npcs = repo.get_actors_by_room(campaign_id, room_id, actor_types=["npc"])
    monsters = repo.get_actors_by_room(campaign_id, room_id, actor_types=["monster"])
    exits = repo.get_exits_by_room(campaign_id, room_id)
    return {
        "room_id": room_id,
        # Phase 51: derive the resonance flag so the dungeon-channel gate
        # (dungeon_channel_available) reads it from this shared context (matches
        # rpg.room_context.build_room_context).
        "resonance_point": any(o["archetype"] == "resonance_point" for o in objects),
        "objects": [
            {
                "object_id": o["object_id"],
                "slug": o["slug"],
                "display_name": o["display_name"],
                "archetype": o["archetype"],
                "current_state": o["current_state"],
                "description": o["description"],
                # Phase 51.5 Part A Slice 3: the obstacle's class-flavored
                # approaches, surfaced as suggested actions in the builder. Raw
                # transitions stay off the thin view-model.
                "approach_verbs": obstacle_approach_verbs(RoomObject(**o)),
            }
            for o in objects
        ],
        "loose_items": [
            {
                "item_id": i["item_id"],
                "slug": i["slug"],
                "display_name": i["display_name"],
                "description": i["description"],
                "status": i["status"],
            }
            for i in raw_items
            if i["item_type"] == "dungeon_item"
        ],
        "npcs": [_actor_noun(a) for a in npcs],
        "monsters": [_actor_noun(a) for a in monsters],
        "exits": [
            {
                "exit_id": e["exit_id"],
                "label": e["label"],
                "status": e["status"],
                "to_room_id": e["to_room_id"],
                **({"requires_item_slug": e["requires_item_slug"]} if e.get("requires_item_slug") else {}),
            }
            for e in exits
        ],
    }
