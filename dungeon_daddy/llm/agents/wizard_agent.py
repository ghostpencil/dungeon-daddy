"""DungeonWizardAgent — guided dungeon creation Q&A."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass

from dungeon_daddy.llm.prompts import load_prompt
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider

_BRIEF_RE = re.compile(r"```brief\s*(.*?)\s*```", re.DOTALL)
_LEVEL_BRIEF_RE = re.compile(r"```level_brief\s*(.*?)\s*```", re.DOTALL)


def _str(val: object) -> str:
    """Coerce a brief field value to a plain string (LLM sometimes outputs nested objects)."""
    if isinstance(val, str):
        return val
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return str(val)


@dataclass
class LevelBrief:
    """Loop pattern, ecology, and GM notes for one dungeon level. Collected per-level in wizard phase 2."""
    level_number: int
    ecology: str
    main_loop_pattern: str
    sub_loop_pattern: str | None = None
    gm_notes: str = ""


@dataclass
class DungeonBrief:
    """Global dungeon settings collected in wizard phase 1. No loop patterns — those move to LevelBrief."""
    title: str
    theme: str
    setting: str
    party: str
    quest: str
    num_levels: int
    gm_notes: str = ""


class DungeonWizardAgent:
    """
    Guides the GM through dungeon creation via structured Q&A.
    Phase 1 collects global settings and outputs a ```brief``` block.
    Phase 2 collects per-level loop patterns and outputs ```level_brief``` blocks.
    """

    PHASE1_SYSTEM_PROMPT = (
        "You are Dungeon Daddy's creation wizard. Guide the game master through\n"
        "designing a new dungeon step by step. Collect:\n"
        "  1. Dungeon name, theme, and setting (location, history, atmosphere)\n"
        "  2. Party composition (size, level, class mix)\n"
        "  3. Main quest or story hook\n"
        "  4. Number of levels\n\n"
        "Ask one or two questions at a time. Don't overwhelm the GM.\n"
        "When you have enough information, summarise the brief and ask for confirmation.\n"
        "On confirmation, output a JSON block marked ```brief``` with these fields:\n"
        "  title, theme, setting, party, quest, num_levels, gm_notes\n"
        "ALL field values must be plain strings (no nested objects or arrays).\n"
        "  setting: single string combining location, history, and atmosphere.\n"
        "  party: single string describing size, level, and class mix.\n"
        "  quest: single string describing the main goal.\n"
        "Do NOT ask about loop patterns here — those are collected per level in the next phase."
    )

    PHASE2_SYSTEM_PROMPT = (
        "You are Dungeon Daddy's level design wizard. "
        "Follow this EXACT sequence for each level. Do not skip or reorder steps.\n\n"
        "STEP 1 — MAIN LOOP (required)\n"
        "  Present all available loop patterns as a numbered list.\n"
        "  For each entry show: number, key, name, and one-line description.\n"
        "  Ask the GM to pick one by number, key, or name — or type 'random'.\n"
        "  Validate the choice: it must match a key in the list exactly.\n"
        "  If the choice is unclear or invalid, show the list again and ask to try again.\n"
        "  Record the validated main_loop_pattern key before moving on.\n\n"
        "STEP 2 — SUB-LOOP (optional)\n"
        "  Ask the GM if they want an optional sub-loop for added complexity.\n"
        "  If yes, show the available patterns and ask them to pick one (same validation as Step 1).\n"
        "  If no, record sub_loop_pattern as null.\n"
        "  Validate and record the sub-loop choice before moving on.\n\n"
        "STEP 3 — LEVEL DETAILS\n"
        "  Ask about the level itself. Cover in order:\n"
        "    - Ecology or environmental flavor (e.g. 'flooded cavern', 'haunted keep')\n"
        "    - Any special rooms or notable areas the GM wants\n"
        "    - Any traps or hazards\n"
        "  Ask one or two questions at a time. "
        "Summarise the GM's answers into a short gm_notes string.\n"
        "  IMPORTANT — Clarify room identity before recording:\n"
        "    If the GM describes a creature, faction, or feature occupying a named area\n"
        "    (e.g. 'scorpions in the marketplace', 'cultists near the library'),\n"
        "    ask whether that is the SAME room (renamed/reskinned) or a SEPARATE adjacent room.\n"
        "    Do not assume — each room must occupy a unique non-overlapping section of the map.\n\n"
        "STEP 4 — OUTPUT\n"
        "  Output the ```level_brief``` block immediately after Step 3 is complete.\n"
        "  Do NOT ask for confirmation. Do NOT announce moving to the next level.\n\n"
        "Output format:\n"
        "```level_brief\n"
        '{"level_number": <N>, "ecology": "<ecology from step 3>", '
        '"main_loop_pattern": "<validated key from step 1>", '
        '"sub_loop_pattern": "<validated key or null from step 2>", '
        '"gm_notes": "<summary of special rooms, features, traps from step 3>"}\n'
        "```\n"
    )

    # Keep backward-compatible alias so callers referencing SYSTEM_PROMPT still work
    SYSTEM_PROMPT = PHASE1_SYSTEM_PROMPT

    def __init__(
        self,
        provider: LLMProvider,
        loop_patterns: dict[str, object],
        context_builder: object | None = None,
    ) -> None:
        self._provider = provider
        self._patterns = loop_patterns
        self._context_builder = context_builder
        self._phase1_prompt = load_prompt("wizard_phase1_system")
        self._phase2_prompt = load_prompt("wizard_phase2_system")

    def chat(self, history: list[LLMMessage], phase: int = 1, dungeon: object | None = None) -> str:
        """Continue the wizard Q&A. phase=1 for global collection, phase=2 for per-level design."""
        if phase == 2:
            system = self._phase2_prompt + "\n\n" + self._build_pattern_list()
        else:
            system = self._phase1_prompt
        if self._context_builder is not None and dungeon is not None:
            context = self._context_builder.build_system_prompt(dungeon)  # type: ignore[attr-defined]
            if context:
                system = context + "\n\n" + system
        return self._provider.complete(
            messages=history,
            system=system,
            max_tokens=1024,
        )

    def parse_brief(self, response: str) -> DungeonBrief | None:
        """
        Extract a DungeonBrief from a response containing a ```brief``` block.
        Returns None if no block is present (conversation still in progress).
        """
        match = _BRIEF_RE.search(response)
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
            return DungeonBrief(
                title=_str(data["title"]),
                theme=_str(data["theme"]),
                setting=_str(data["setting"]),
                party=_str(data["party"]),
                quest=_str(data["quest"]),
                num_levels=int(data["num_levels"]),
                gm_notes=_str(data.get("gm_notes", "")),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def parse_level_brief(self, response: str) -> LevelBrief | None:
        """
        Extract a LevelBrief from a response containing a ```level_brief``` block.
        If main_loop_pattern is absent, picks one at random from available patterns.
        Returns None if no block is present or JSON is malformed.
        """
        match = _LEVEL_BRIEF_RE.search(response)
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
            main = data.get("main_loop_pattern") or self._random_pattern_key()
            return LevelBrief(
                level_number=int(data["level_number"]),
                ecology=data["ecology"],
                main_loop_pattern=main,
                sub_loop_pattern=data.get("sub_loop_pattern"),
                gm_notes=data.get("gm_notes", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _random_pattern_key(self) -> str:
        return random.choice(list(self._patterns.keys()))

    def _build_pattern_list(self) -> str:
        """Format the loop patterns as a numbered list for the system prompt."""
        if not self._patterns:
            return "# Available Loop Patterns\n(none loaded)"
        lines = ["# Available Loop Patterns"]
        for i, (key, pattern) in enumerate(self._patterns.items(), start=1):
            lines.append(f"{i}. {key} — {pattern.name}: {pattern.blurb}")  # type: ignore[attr-defined]
        return "\n".join(lines)
