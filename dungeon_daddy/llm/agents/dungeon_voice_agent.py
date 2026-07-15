"""DungeonVoiceAgent — Phase 51 "Talk to the Dungeon" freeform channel.

A thin, advisory agent: it assembles the §4.4 dungeon-voice bundle and calls the
injected ``LLMProvider``, returning pure narration. It resolves no mechanics,
emits no proposals, and never mutates authoritative state (D6 / authority
boundary). Knowledge filtering (``reveal_knowledge``) and memory retrieval
(``MemoryRetriever``) are the caller's job; this agent only formats and asks.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from dungeon_daddy.llm.lookup_tool import LOOKUP_WORLD_TOOL
from dungeon_daddy.llm.prompts import load_prompt
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider, LLMToolCall
from dungeon_daddy.llm.tool_loop import run_tool_loop

if TYPE_CHECKING:
    from dungeon_daddy.memory.models import MemoryEntry

# The §6 scoping contract, restated for the model when the lookup tool is live.
_LOOKUP_GUIDANCE = (
    "\n\n# Looking Things Up\n"
    "You have a `lookup_world` tool. Use it ONLY for people, places, or past "
    "events NOT already in your context — someone the speaker names who is not "
    "present, distant lore, or a past event your knowledge and recent memories "
    "do not already cover. Never look up something already in your context. If "
    "you already have what you need, just answer."
)


class DungeonVoiceAgent:
    SYSTEM_PROMPT: str = load_prompt("dungeon_voice_system")

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def respond(
        self,
        *,
        dungeon_voice: str,
        intimacy_filled: int,
        intimacy_segments: int,
        dungeon_knowledge: list[str],
        player_message: str,
        actor: str,
        recent_memories: list[MemoryEntry] | None = None,
        actor_name: str = "",
        actor_playbook: str | None = None,
        actor_tags: list[str] | None = None,
        systems_status: list[tuple[str, str]] | None = None,
        next_objective: str | None = None,
        next_objective_location: str | None = None,
        session_turns: list[tuple[str, str]] | None = None,
        lookup: Callable[[LLMToolCall], str] | None = None,
    ) -> str:
        system = self._build_system(
            dungeon_voice=dungeon_voice,
            intimacy_filled=intimacy_filled,
            intimacy_segments=intimacy_segments,
            dungeon_knowledge=dungeon_knowledge,
            recent_memories=recent_memories or [],
            actor_name=actor_name,
            actor_playbook=actor_playbook,
            actor_tags=actor_tags or [],
            systems_status=systems_status or [],
            next_objective=next_objective,
            next_objective_location=next_objective_location,
            session_turns=session_turns or [],
        )
        user = f"{actor} says: {player_message}"
        history = [LLMMessage(role="user", content=user)]
        if lookup is not None and getattr(self._provider, "supports_tools", False):
            # Escalation path (§9/§10): agent-owned tool loop; provider is pure
            # transport. Guidance restates the §6 contract only when live.
            return run_tool_loop(
                self._provider,
                history,
                system + _LOOKUP_GUIDANCE,
                tools=[LOOKUP_WORLD_TOOL],
                executor=lookup,
                max_tokens=1024,
            )
        return self._provider.complete(
            messages=history,
            system=system,
            max_tokens=1024,
        )

    def _build_system(
        self,
        *,
        dungeon_voice: str,
        intimacy_filled: int,
        intimacy_segments: int,
        dungeon_knowledge: list[str],
        recent_memories: list[MemoryEntry],
        actor_name: str = "",
        actor_playbook: str | None = None,
        actor_tags: list[str] | None = None,
        systems_status: Sequence[tuple[str, ...]] | None = None,
        next_objective: str | None = None,
        next_objective_location: str | None = None,
        session_turns: list[tuple[str, str]] | None = None,
    ) -> str:
        lines = [self.SYSTEM_PROMPT]
        lines.append("\n# Your Voice")
        lines.append(dungeon_voice)
        if actor_name:
            lines.append("\n# Who Is Speaking")
            who = actor_name
            if actor_playbook:
                who += f" — {actor_playbook}"
            lines.append(who)
            if actor_tags:
                lines.append("Tags: " + ", ".join(actor_tags))
        if systems_status:
            lines.append("\n# Systems Status")
            for entry in systems_status:
                name, state = entry[0], entry[1]
                location = entry[2] if len(entry) > 2 else ""
                line = f"- {name}: {state}"
                if location:
                    line += f" (located in {location})"
                lines.append(line)
        lines.append("\n# Intimacy")
        lines.append(f"{intimacy_filled}/{intimacy_segments}")
        if dungeon_knowledge:
            lines.append("\n# Knowledge you may draw on")
            for item in dungeon_knowledge:
                lines.append(f"- {item}")
        if next_objective:
            lines.append("\n# What You Want Next")
            lines.append(next_objective)
            if next_objective_location:
                lines.append(f"Location: {next_objective_location}")
        if recent_memories:
            lines.append("\n# Recent Memories")
            for mem in recent_memories:
                lines.append(f"- {mem.title}: {mem.summary}")
        if session_turns:
            lines.append("\n# This Conversation So Far")
            for speaker, text in session_turns:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
