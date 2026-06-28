"""DungeonVoiceAgent — Phase 51 "Talk to the Dungeon" freeform channel.

A thin, advisory agent: it assembles the §4.4 dungeon-voice bundle and calls the
injected ``LLMProvider``, returning pure narration. It resolves no mechanics,
emits no proposals, and never mutates authoritative state (D6 / authority
boundary). Knowledge filtering (``reveal_knowledge``) and memory retrieval
(``MemoryRetriever``) are the caller's job; this agent only formats and asks.
"""
from __future__ import annotations

from dungeon_daddy.llm.prompts import load_prompt
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider


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
        recent_memories=None,
        actor_name: str = "",
        actor_playbook: str | None = None,
        actor_tags: list[str] | None = None,
        systems_status: list[tuple[str, str]] | None = None,
        next_objective: str | None = None,
        session_turns: list[tuple[str, str]] | None = None,
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
            session_turns=session_turns or [],
        )
        user = f"{actor} says: {player_message}"
        return self._provider.complete(
            messages=[LLMMessage(role="user", content=user)],
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
        recent_memories,
        actor_name: str = "",
        actor_playbook: str | None = None,
        actor_tags=None,
        systems_status=None,
        next_objective: str | None = None,
        session_turns=None,
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
            for name, state in systems_status:
                lines.append(f"- {name}: {state}")
        lines.append("\n# Intimacy")
        lines.append(f"{intimacy_filled}/{intimacy_segments}")
        if dungeon_knowledge:
            lines.append("\n# Knowledge you may draw on")
            for item in dungeon_knowledge:
                lines.append(f"- {item}")
        if next_objective:
            lines.append("\n# What You Want Next")
            lines.append(next_objective)
        if recent_memories:
            lines.append("\n# Recent Memories")
            for mem in recent_memories:
                lines.append(f"- {mem.title}: {mem.summary}")
        if session_turns:
            lines.append("\n# This Conversation So Far")
            for speaker, text in session_turns:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
