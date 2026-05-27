"""DungeonMasterAgent — Play Mode narration and chat."""
from __future__ import annotations

from dungeon_daddy.data.models import Dungeon, Level, Loop, Room
from dungeon_daddy.llm.context_builder import ContextBuilder
from dungeon_daddy.llm.prompts import load_prompt
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider


class DungeonMasterAgent:
    """
    Drives the Play Mode chat. Responds in-character as the dungeon,
    narrating rooms, adjudicating actions, and advancing the story.
    """

    SYSTEM_PROMPT = (
        "You are the Dungeon Master for a tabletop dungeon crawl.\n"
        "Respond in-character: vivid, atmospheric, concise.\n"
        "Use the room and dungeon context to ground every response.\n"
        "If play memory is provided for this room, acknowledge what the party has\n"
        "already seen or done here — do not describe things they already know.\n"
        "Never break character. Never explain the rules.\n"
        "\n"
        "When the party takes any concrete action — marking a location, manipulating\n"
        "or moving objects, triggering or disarming traps, discovering secrets, or\n"
        "causing an NPC to react — append exactly this tag to the END of your response\n"
        "(never mid-sentence):\n"
        "\n"
        "  [REMEMBER: one short sentence describing what the party did]\n"
        "\n"
        "Include the tag whenever a physical action changes the room or its state.\n"
        "Omit it only for pure questions or atmospheric descriptions with no party action."
    )

    def __init__(self, provider: LLMProvider, context_builder: ContextBuilder | None = None) -> None:
        self._provider = provider
        self._context_builder = context_builder
        self._system_prompt = load_prompt("dm_system")

    def respond(
        self,
        history: list[LLMMessage],
        room: Room,
        level: Level,
        dungeon: Dungeon,
        room_memory: str = "",
        level_id: int | None = None,
        active_loop: Loop | None = None,
    ) -> str:
        context = self._build_context(room, level, dungeon, room_memory)
        system = self._system_prompt + "\n\n" + context
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
