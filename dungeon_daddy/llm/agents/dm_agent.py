"""DungeonMasterAgent — Play Mode narration and chat."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dungeon_daddy.data.models import Dungeon, Level, Loop, Room
from dungeon_daddy.llm.context_builder import ContextBuilder
from dungeon_daddy.llm.prompts import load_prompt
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider

if TYPE_CHECKING:
    from dungeon_daddy.memory.models import ContextBundle
    from dungeon_daddy.rpg.models import ActionResolution


class DungeonMasterAgent:
    """
    Drives the Play Mode chat. Responds in-character as the dungeon,
    narrating rooms, adjudicating actions, and advancing the story.
    """

    SYSTEM_PROMPT: str = load_prompt("dm_system")

    def __init__(self, provider: LLMProvider, context_builder: ContextBuilder | None = None) -> None:
        self._provider = provider
        self._context_builder = context_builder

    def build_prompt(self, context_bundle: ContextBundle | None = None) -> str:
        if context_bundle is None:
            return self.SYSTEM_PROMPT
        lines = [self.SYSTEM_PROMPT]
        brief = context_bundle.scene_brief
        if brief:
            lines.append("\n# Scene")
            lines.append(f"Location: {brief.get('location_slug', '')}")
            lines.append(f"Status: {brief.get('status', '')}")
        cards = context_bundle.memory_cards
        if cards:
            lines.append("\n# Memory")
            for i, card in enumerate(cards, 1):
                label = "[DRAFT] " if card.get("draft") else ""
                lines.append(
                    f"{i}. {label}{card['title']} (importance: {card['importance']})"
                    f"\n   {card['summary']}"
                )
        lore = context_bundle.related_lore
        if lore:
            lines.append("\n# Related Lore")
            for entry in lore:
                lines.append(
                    f"  - {entry['title']} (importance: {entry['importance']})"
                    f"\n    {entry['summary']}"
                )
        fallout = context_bundle.active_fallout
        clocks = context_bundle.open_clocks
        if fallout or clocks:
            lines.append("\n# Mechanical Context")
            if fallout:
                lines.append("Active Fallout:")
                for f in fallout:
                    lines.append(f"  - {f.get('title', '')} [{f.get('status', '')}]")
            if clocks:
                lines.append("Open Clocks:")
                for c in clocks:
                    lines.append(f"  - {c.get('label', c.get('name', ''))} ({c.get('filled', 0)}/{c.get('segments', 0)})")
        objects = (context_bundle.current_room or {}).get("objects", [])
        if objects:
            lines.append("\n# Room Contents")
            for o in objects:
                desc = o.get("description", "")
                lines.append(f"  - {o.get('display_name', '')}: {desc}" if desc
                             else f"  - {o.get('display_name', '')}")
        return "\n".join(lines)

    def respond(
        self,
        history: list[LLMMessage],
        room: Room,
        level: Level,
        dungeon: Dungeon,
        room_memory: str = "",
        level_id: int | None = None,
        active_loop: Loop | None = None,
        context_bundle: ContextBundle | None = None,
    ) -> str:
        context = self._build_context(room, level, dungeon, room_memory)
        base = self.build_prompt(context_bundle)
        system = base + "\n\n" + context
        if active_loop is not None:
            system += "\n\n" + self._build_loop_context(active_loop, room, level)
        if self._context_builder is not None:
            doc_context = self._context_builder.build_system_prompt(dungeon, level_id=level_id)
            if doc_context:
                system = doc_context + "\n\n" + system
        return self._provider.complete(
            messages=history,
            system=system,
            max_tokens=1024,
        )

    def _build_context(
        self,
        room: Room,
        level: Level,
        dungeon: Dungeon,
        room_memory: str,
    ) -> str:
        lines = [
            "# Current Room",
            f"Room: {room.name} ({room.type})",
            f"Dimensions: {room.w}\u00d7{room.h} grid cells",
            f"Note: {room.note}",
            "",
            "# Level",
            f"Level: {level.name} (Level {level.id})",
            f"Ecology: {level.ecology}",
            "",
            "# Dungeon",
            f"Title: {dungeon.meta.title}",
            f"Quest: {dungeon.meta.quest}",
        ]

        if room_memory:
            lines += [
                "",
                "# Play History",
                room_memory.rstrip(),
            ]

        return "\n".join(lines)

    def request_proposal(
        self,
        resolution: ActionResolution,
        context_bundle: ContextBundle | None,
        known_clocks: list[dict[str, Any]],
        known_actors: list[dict[str, Any]],
        player_actor_ids: list[str],
        room_name: str = "",
        room_note: str = "",
    ) -> str:
        system = "\n".join([
            "You are the Dungeon Daddy advisory engine.",
            "After each player action you propose structured world reactions.",
            "Rules: never control player actors; only use IDs from the lists provided; return ONLY valid JSON.",
            "",
            "Response schema:",
            '{"narration_hint": "<string>", "proposed_changes": [...]}',
            "",
            "Each change is a FLAT object with a 'kind' field plus its own fields. Examples:",
            '{"kind": "advance_clock", "clock_id": "<id>", "amount": 1, "reason": "<why>"}',
            '{"kind": "apply_consequence", "actor_id": "<id>", "track_key": "<key>", "amount": 1, "reason": "<why>"}',
            '{"kind": "create_memory", "title": "<title>", "summary": "<text>", "importance": 5, "tags": ["<tag>"]}',
            '{"kind": "npc_reaction", "npc_id": "<id>", "reaction": "<text>", "reason": "<why>"}',
            "Do NOT nest fields under the kind name — include 'kind' as a sibling field.",
        ])

        user_lines = [
            f"Action: {resolution.action_key}",
            f"Outcome: {resolution.outcome}",
            f"Intent: {resolution.intent or '(none)'}",
        ]
        if room_name:
            user_lines.append(f"Room: {room_name}" + (f" — {room_note}" if room_note else ""))
        user_lines.append("")

        if known_clocks:
            user_lines.append("Known clocks (use exact IDs):")
            for c in known_clocks:
                user_lines.append(
                    f"  - {c['clock_id']}: \"{c.get('label', '?')}\" "
                    f"[{c.get('filled', 0)}/{c.get('segments', 0)}]"
                )
        else:
            user_lines.append("Known clocks: (none)")
        user_lines.append("")

        if known_actors:
            user_lines.append("Known actors (use exact IDs):")
            for a in known_actors:
                tag = " [player — do not control]" if a["actor_id"] in player_actor_ids else ""
                user_lines.append(f"  - {a['actor_id']}: \"{a.get('display_name', a['actor_id'])}\"{tag}")
        user_lines.append("")
        user_lines.append("Propose 1-3 world reactions suited to the outcome.")

        try:
            return self._provider.complete(
                messages=[LLMMessage(role="user", content="\n".join(user_lines))],
                system=system,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
        except Exception:
            return ""

    def _build_loop_context(self, loop: Loop, room: Room, level: Level) -> str:
        room_names = {r.id: r.name for r in level.rooms}
        entry_name = room_names.get(loop.entry, loop.entry)
        goal_name = room_names.get(loop.goal, loop.goal)
        on_a = room.id in loop.path_a
        on_b = room.id in loop.path_b
        if on_a and on_b:
            current_room_placement = "Path A and Path B"
        elif on_a:
            current_room_placement = "Path A"
        elif on_b:
            current_room_placement = "Path B"
        else:
            current_room_placement = "neither path"

        path_a_names = " → ".join(room_names.get(rid, rid) for rid in loop.path_a)
        path_b_names = " → ".join(room_names.get(rid, rid) for rid in loop.path_b)

        lines = [
            "# Active Loop",
            f"Pattern: {loop.pattern}",
            f"Explanation: {loop.explanation}",
            f"Entry: {entry_name}",
            f"Goal: {goal_name}",
            f"Path A: {path_a_names}",
            f"Path B: {path_b_names}",
            f"Current Room: {current_room_placement}",
        ]
        return "\n".join(lines)
