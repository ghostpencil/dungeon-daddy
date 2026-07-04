"""Persona Markdown helpers — Phase 51 "Talk to the Dungeon" (P1).

The dungeon's voice and seed knowledge reach play time as YAML-front-matter
Markdown docs under ``‹save_dir›/memory/dungeon/`` (the established house
pattern — narrative text in Markdown, DuckDB holds path references). These pure
helpers read and write those docs on top of ``markdown_store``; they hold no
state and do no DB work.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dungeon_daddy.memory.markdown_store import read_memory, write_memory

_VOICE_FILENAME = "voice.md"
_KNOWLEDGE_FILENAME = "knowledge.md"

_VOICE_TYPE = "dungeon_voice"
_KNOWLEDGE_TYPE = "dungeon_knowledge"


def write_dungeon_voice(dungeon_dir: Path, campaign_id: str, voice: str) -> Path:
    """Write the dungeon's static persona prompt to ``voice.md``; return its path."""
    dungeon_dir.mkdir(parents=True, exist_ok=True)
    path = dungeon_dir / _VOICE_FILENAME
    fm = {
        "id": _VOICE_TYPE,
        "type": _VOICE_TYPE,
        "campaign_id": campaign_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_memory(path, fm, voice)
    return path


def read_dungeon_voice(path: Path) -> str | None:
    """Return the voice text, or ``None`` when the file is missing."""
    if not path.exists():
        return None
    _, body = read_memory(path)
    return body


def write_dungeon_knowledge(
    dungeon_dir: Path, campaign_id: str, knowledge: list[str]
) -> Path:
    """Write seed secrets to ``knowledge.md`` (one ``- secret`` bullet each)."""
    dungeon_dir.mkdir(parents=True, exist_ok=True)
    path = dungeon_dir / _KNOWLEDGE_FILENAME
    fm = {
        "id": _KNOWLEDGE_TYPE,
        "type": _KNOWLEDGE_TYPE,
        "campaign_id": campaign_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    body = "\n".join(f"- {secret}" for secret in knowledge)
    write_memory(path, fm, body)
    return path


def read_dungeon_knowledge(path: Path) -> list[str]:
    """Return the seed secrets (one per bullet); missing file → ``[]``."""
    if not path.exists():
        return []
    _, body = read_memory(path)
    secrets: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            secrets.append(stripped[2:].strip())
    return secrets
