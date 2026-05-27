"""DungeonGeneratorAgent — level-by-level JSON generation."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from dungeon_daddy.data.models import Dungeon, Level
from dungeon_daddy.llm.agents.wizard_agent import DungeonBrief, LevelBrief
from dungeon_daddy.llm.provider import LLMProvider

_JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
_log = logging.getLogger(__name__)


def _coerce_sub_loop_roles(data: dict[str, Any]) -> None:
    """For rooms in a sub-loop with sub_loop_roles=null, derive role from loop entry/goal."""
    room_by_id = {r["id"]: r for r in data.get("rooms", [])}
    for lp in data.get("loops", []):
        if lp.get("type") != "sub":
            continue
        entry_id = lp.get("entry")
        goal_id = lp.get("goal")
        for rid in lp.get("rooms", []):
            room = room_by_id.get(rid)
            if room is None or room.get("sub_loop_roles") is not None:
                continue
            if rid == entry_id:
                role = "entry"
            elif rid == goal_id:
                role = "goal"
            else:
                role = "path"
            room["sub_loop_roles"] = [{"role": role}]


def _check_no_duplicate_main_loop_roles(level: Level) -> None:
    """Raise ValueError if two rooms in the same loop share a non-null main_loop_role."""
    room_by_id = {r.id: r for r in level.rooms}
    for lp in level.loops:
        if lp.type != "main":
            continue
        seen_roles: set[str] = set()
        for rid in lp.rooms:
            room = room_by_id.get(rid)
            if room is None or room.main_loop_role is None:
                continue
            if room.main_loop_role in seen_roles:
                raise ValueError(
                    f"Level {level.id}, loop '{lp.id}': "
                    f"duplicate main_loop_role '{room.main_loop_role}' — "
                    "each role must appear at most once per loop."
                )
            seen_roles.add(room.main_loop_role)


class DungeonGeneratorAgent:
    """
    Generates one dungeon level at a time from a DungeonBrief.
    Supports revision: if validation fails, caller passes errors back in.
    """

    SYSTEM_PROMPT = (
        "You are a dungeon architect. Generate one level of a dungeon as JSON.\n"
        "The JSON must conform exactly to the Level schema provided.\n"
        "Rooms use a grid coordinate system. Connections must be physically plausible.\n"
        "Every room must have a unique, non-overlapping (x, y, w, h) rectangle. "
        "No two rooms may share any grid cell.\n"
        "Rooms must also be separated by at least 1 empty cell on every side. "
        "If room A has x=0 and w=5 (right edge=5), the next room must have x≥6 — "
        "touching edges (gap=0) are forbidden. "
        "Plan positions with generous spacing to avoid gap violations.\n"
        "Apply the specified loop pattern: assign rooms to path_a and path_b.\n"
        "Output only a single ```json``` block containing the Level object. No prose."
    )

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate_level(
        self,
        brief: DungeonBrief,
        level_brief: LevelBrief,
        dungeon_so_far: Dungeon,
        validation_errors: list[str] | None = None,
    ) -> str:
        context = self._build_context(brief, level_brief, dungeon_so_far, validation_errors)
        response = self._provider.complete(
            messages=[],
            system=self.SYSTEM_PROMPT + "\n\n" + context,
            max_tokens=4096,
        )
        _log.debug("Generator raw response (level %s):\n%s", level_brief.level_number, response)
        return response

    def parse_level(self, response: str) -> Level:
        """
        Extract and parse the Level JSON from a ```json``` block.
        Raises ValueError if no valid block is found.
        Raises pydantic.ValidationError if the JSON doesn't match the Level schema.
        """
        match = _JSON_RE.search(response)
        if not match:
            raise ValueError(
                "No ```json``` block found in generator response. "
                f"Response was: {response[:200]!r}"
            )
        data = json.loads(match.group(1))
        _coerce_sub_loop_roles(data)
        level = Level.model_validate(data)
        _check_no_duplicate_main_loop_roles(level)
        _log.info("Parsed level JSON (level %s):\n%s", level.id, json.dumps(data, indent=2))
        return level

    def _build_context(
        self,
        brief: DungeonBrief,
        level_brief: LevelBrief,
        dungeon_so_far: Dungeon,
        validation_errors: list[str] | None,
    ) -> str:
        sub = level_brief.sub_loop_pattern or "none"
        lines = [
            "# Dungeon Brief",
            f"Title: {brief.title}",
            f"Theme: {brief.theme}",
            f"Party: {brief.party}",
            f"Quest: {brief.quest}",
            f"Total levels: {brief.num_levels}",
            "",
            "# Generating",
            f"Level number: {level_brief.level_number} of {brief.num_levels}",
            f"Ecology: {level_brief.ecology}",
            f"Main loop pattern: {level_brief.main_loop_pattern}",
            f"Sub-loop pattern: {sub}",
        ]
        if getattr(level_brief, "gm_notes", ""):
            lines.append(f"GM notes: {level_brief.gm_notes}")

        # Stair continuity from levels already generated
        if dungeon_so_far is not None and dungeon_so_far.levels:
            prev_ids = ", ".join(str(lv.id) for lv in dungeon_so_far.levels)
            lines.append(f"Previous levels: {prev_ids}")
        else:
            lines.append("Previous levels: none")

        lines += [
            "",
            "# Level Schema (JSON field names and types)",
            "id: int, name: str, summary: str, ecology: str, loop: str,",
            "width: int, height: int, entries: list[Entry],",
            "rooms: list[Room], connections: list[Connection], loops: list[Loop]",
            "Room: id str, num int, name str, x int, y int, w int, h int,",
            "      type str (hall|shrine|lair|vault|stair|study|boss), note str,",
            "      main_loop_role str|null, sub_loop_roles list[dict]|null",
            'Connection: from str, to str, type str (door|hall|arch|hole|stair_down|stair_up), note str',
            "Entry: x float, y float, type str (stair_up|stair_down), label str",
            "Loop: id str, pattern str, note str, entry str (room id), goal str (room id),",
            "      path_a list[str] (room ids), path_b list[str] (room ids),",
            '      type str ("main"|"sub"), explanation str, rooms list[str] (room ids)',
            "",
            "# Loop Room Role Rules",
            "Every room ID listed in a loop's rooms array must have its role field set:",
            '  - If loop.type="main" → room.main_loop_role must be a non-null string',
            '    (e.g. "entry", "obstacle", "goal", "bypass", "clue", "foreshadow")',
            "    IMPORTANT: each main_loop_role value must be UNIQUE within a loop —",
            "    no two rooms in the same loop may share the same main_loop_role string.",
            '  - If loop.type="sub" → room.sub_loop_roles must be a non-null list',
            "    with at least one dict entry (e.g. [{\"role\": \"goal\"}])",
            "Rooms NOT listed in any loop.rooms may have null roles.",
            "",
            "# Validation Errors to Fix",
        ]

        if validation_errors:
            for err in validation_errors:
                lines.append(f"- {err}")
        else:
            lines.append("(none)")

        return "\n".join(lines)
