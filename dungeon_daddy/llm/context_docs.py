"""Generate context docs (setting, party, level design) from Dungeon data."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level
    from dungeon_daddy.data.repository import DungeonRepository


def generate_setting_doc(meta: "DungeonMeta") -> str:
    return (
        f"# {meta.title}\n\n"
        f"## Theme\n{meta.theme}\n\n"
        f"## Setting\n{meta.setting}\n\n"
        f"## Quest\n{meta.quest}\n"
    )


def generate_party_doc(meta: "DungeonMeta") -> str:
    return (
        f"# Party\n\n"
        f"{meta.party}\n\n"
        f"## Stats\n"
        f"- Party size: {meta.party_size}\n"
        f"- Party level: {meta.party_level}\n"
    )


def generate_level_design_doc(level: "Level") -> str:
    return (
        f"# Level {level.id}: {level.name}\n\n"
        f"## Ecology\n{level.ecology}\n\n"
        f"## Design Notes\n{level.summary}\n"
    )


def generate_all_context_docs(
    dungeon: "Dungeon",
    dungeon_name: str,
    repo: "DungeonRepository",
    skip_existing: bool = True,
) -> None:
    from dungeon_daddy.data.models import ContextDocType

    def _save(doc_type: ContextDocType, content: str, level_id: int | None = None) -> None:
        if skip_existing and repo.load_context_doc(dungeon_name, doc_type, level_id):
            return
        repo.save_context_doc(dungeon_name, doc_type, content, level_id)

    _save(ContextDocType.SETTING, generate_setting_doc(dungeon.meta))
    _save(ContextDocType.PARTY, generate_party_doc(dungeon.meta))
    for level in dungeon.levels:
        _save(ContextDocType.LEVEL_DESIGN, generate_level_design_doc(level), level_id=level.id)
