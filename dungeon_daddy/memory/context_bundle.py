from __future__ import annotations

import uuid
from typing import Any, Literal

from dungeon_daddy.memory.models import ContextBundle
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.memory.retrieval import MemoryRetriever, present_actor_ids
from dungeon_daddy.rpg.models import RoomObject
from dungeon_daddy.rpg.obstacles import obstacle_approach_verbs
from dungeon_daddy.rpg.service import compute_effective_ratings

# Slice A6 (T7): the `# Related Lore` section has its own dedicated sub-budget
# (~400 tokens, per spec §5 T7 step 3), retrieved and trimmed independently of
# the scoped memory-card section so pre-fetched lore never crowds out the
# scene's own memories.
_RELATED_LORE_TOKEN_BUDGET = 400


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
        already_bundled = {c["memory_id"] for c in memory_cards}
        related_lore, lore_provenance = self._fetch_related_lore(repo, already_bundled)
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
            related_lore=related_lore,
            must_remember=must_remember,
            faction_reputations=self._fetch_faction_reputations(repo),
            inventory=self._fetch_inventory(repo),
            current_room=self._fetch_current_room(repo),
            provenance={**provenance, **lore_provenance},
        )

    def _fetch_memories(
        self, repo: MemoryRepository
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
        retriever = MemoryRetriever(repo, self._campaign_id)
        # Slice A5 (§5.2): the importance>=9 pins are ALWAYS included (an
        # unscoped query — a critical memory is never gated by scene scope),
        # while the regular bulk is scoped to the current room + present actors.
        # With no room and no focus actors the scoped query is also unscoped,
        # preserving pre-A5 recap/no-scene behavior.
        pinned = [e for e in retriever.query() if e.importance >= 9]
        pin_ids = {e.memory_id for e in pinned}
        scoped = retriever.query(
            actor_ids=present_actor_ids(
                repo, self._campaign_id, self._current_room_id, self._focus_actor_ids
            ),
            location_slug=self._current_room_id,
        )
        regular = [
            e for e in scoped if e.importance < 9 and e.memory_id not in pin_ids
        ]
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
            "retrieved": len(pinned) + len(regular),
            "omitted": omitted,
            "focus_actor_ids": self._focus_actor_ids,
        }
        return cards, must_remember, provenance

    def _fetch_related_lore(
        self, repo: MemoryRepository, exclude_ids: set[str]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Slice A6 (T7): the deterministic tag-driven `# Related Lore` section.

        Unions the descriptive tags of the scene's anchor entities (room
        objects/items, present NPCs/monsters, the party, the active objective),
        retrieves memories sharing those tags ranked by tag-hit count, drops
        anything already in ``memory_cards`` (``exclude_ids``), and trims to the
        section sub-budget. Records anchor tags + retrieved/omitted counts in
        provenance. With no current room there is no scene to expand → empty.
        """
        if self._current_room_id is None:
            return [], {
                "related_lore_anchor_tags": [],
                "related_lore_retrieved": 0,
                "related_lore_omitted": 0,
            }
        anchor_tags = _collect_anchor_tags(
            repo, self._campaign_id, self._current_room_id, self._focus_actor_ids
        )
        retriever = MemoryRetriever(repo, self._campaign_id)
        candidates = [
            e
            for e in retriever.query_by_tag_relevance(anchor_tags)
            if e.memory_id not in exclude_ids
        ]
        kept, omitted = retriever.trim_to_budget(
            candidates, _RELATED_LORE_TOKEN_BUDGET
        )
        cards = [
            {
                "memory_id": e.memory_id,
                "title": e.title,
                "summary": e.summary,
                "importance": e.importance,
            }
            for e in kept
        ]
        provenance = {
            "related_lore_anchor_tags": anchor_tags,
            "related_lore_retrieved": len(candidates),
            "related_lore_omitted": omitted,
        }
        return cards, provenance

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
            actor = repo.get_actor(actor_id)
            state[actor_id] = {
                # The PC's name — the `# Party` prompt section renders it so a
                # party actor id collected by bundle_entity_ids is readable by
                # the narrator (L7). Falls back to the id for an unknown actor.
                "display_name": actor["display_name"] if actor else actor_id,
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
                    "item_id": i["item_id"],
                    "slug": i["slug"],
                    "display_name": i["display_name"],
                    "description": i["description"],
                    "charges_current": i["charges_current"],
                    "charges_max": i["charges_max"],
                }
                for i in items
                if i["item_type"] == "class_kit" and i["status"] == "active"
            ]
            dungeon_items = [
                {
                    "item_id": i["item_id"],
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
                    "item_id": i["item_id"],
                    "slug": i["slug"],
                    "display_name": i["display_name"],
                    "description": i["description"],
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


def _collect_anchor_tags(
    repo: MemoryRepository,
    campaign_id: str,
    room_id: str,
    focus_actor_ids: list[str],
) -> list[str]:
    """The union of the scene's anchor-entity tags (Slice A6 / T7 step 1).

    The same nouns the room noun-context assembles — room objects, loose room
    items, present NPCs/monsters — plus the focus party and the active
    objective. Order-preserving, deduped. A cross-campaign or unknown focus
    actor id contributes nothing.
    """
    tags: list[str] = []
    for obj in repo.get_objects_by_room(campaign_id, room_id):
        tags.extend(obj.get("tags", []))
    for item in repo.get_items_by_room(campaign_id, room_id):
        tags.extend(item.get("tags", []))
    for actor in repo.get_actors_by_room(
        campaign_id, room_id, actor_types=["npc", "monster"]
    ):
        tags.extend(actor.get("tags", []))
    for actor_id in focus_actor_ids:
        party_actor = repo.get_actor(actor_id)
        if party_actor is not None and party_actor["campaign_id"] == campaign_id:
            tags.extend(party_actor.get("tags", []))
    for objective in repo.get_objectives(campaign_id):
        if objective.get("status") == "active":
            tags.extend(objective.get("tags", []))
    return list(dict.fromkeys(tags))


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
