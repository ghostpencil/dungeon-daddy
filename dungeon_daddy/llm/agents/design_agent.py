"""DesignAgent — post-generation dungeon refinement chat."""
from __future__ import annotations

from dungeon_daddy.llm.provider import LLMMessage, LLMProvider


class DesignAgent:
    """
    Post-generation design assistant. Helps the GM refine the dungeon
    via conversational chat after initial generation is complete.
    """

    SYSTEM_PROMPT = (
        "You are Dungeon Daddy's design assistant. You help game masters refine\n"
        "dungeon crawls using cyclic loop patterns (Lock & Key, Gambit, Foreshadowing,\n"
        "etc.). You speak concisely and return structured suggestions.\n"
        "When asked to generate or modify dungeon content, respond with a clear\n"
        "description of the change and, where relevant, the affected room IDs."
    )

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def chat(
        self,
        history: list[LLMMessage],
        dungeon: object,
    ) -> str:
        context = self._build_context(dungeon)
        return self._provider.complete(
            messages=history,
            system=self.SYSTEM_PROMPT + "\n\n" + context,
            max_tokens=1024,
        )

    def _build_context(self, dungeon: object) -> str:
        meta = dungeon.meta  # type: ignore[attr-defined]
        lines = [
            "# Dungeon",
            f"Title: {meta.title}",
            f"Theme: {meta.theme}",
            f"Setting: {meta.setting}",
            f"Party: {meta.party}",
            f"Quest: {meta.quest}",
            "",
            "# Levels",
        ]
        for level in dungeon.levels:  # type: ignore[attr-defined]
            room_count = len(level.rooms)
            lines.append(
                f"Level {level.id} — {level.name}: "
                f"{room_count} room{'s' if room_count != 1 else ''}, "
                f"primary loop: {level.loop}"
            )
        return "\n".join(lines)
