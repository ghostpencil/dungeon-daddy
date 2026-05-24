"""Assemble compacted context docs into a system prompt."""
from __future__ import annotations

from dungeon_daddy.data.models import ContextDocType, Dungeon
from dungeon_daddy.data.repository import DungeonRepository
from dungeon_daddy.llm.context_compactor import ContextCompactor


class ContextBuilder:
    def __init__(
        self,
        repo: DungeonRepository,
        compactor: ContextCompactor,
        max_tokens_per_doc: int = 800,
    ):
        self._repo = repo
        self._compactor = compactor
        self._max_tokens = max_tokens_per_doc

    def build_system_prompt(self, dungeon: Dungeon, level_id: int | None = None) -> str:
        name = dungeon.meta.effective_name
        parts: list[str] = []

        setting = self._repo.load_context_doc(name, ContextDocType.SETTING)
        if setting:
            parts.append(self._compactor.compact(setting, self._max_tokens))

        party = self._repo.load_context_doc(name, ContextDocType.PARTY)
        if party:
            parts.append(self._compactor.compact(party, self._max_tokens))

        if level_id is not None:
            level_design = self._repo.load_context_doc(name, ContextDocType.LEVEL_DESIGN, level_id=level_id)
            if level_design:
                parts.append(self._compactor.compact(level_design, self._max_tokens))

        return "\n\n".join(parts)
