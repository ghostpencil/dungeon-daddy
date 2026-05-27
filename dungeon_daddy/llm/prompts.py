"""Prompt file loader — reads system prompts from dungeon_daddy/prompts/."""
from __future__ import annotations

import hashlib
import importlib.resources as pkg_resources


def load_prompt(name: str) -> str:
    """Load a system prompt by name from dungeon_daddy/prompts/<name>.txt."""
    ref = pkg_resources.files("dungeon_daddy.prompts").joinpath(f"{name}.txt")
    try:
        return ref.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt not found: {name!r}")


def prompt_hash(text: str) -> str:
    """Return the first 8 hex characters of the SHA-256 hash of the prompt text."""
    return hashlib.sha256(text.encode()).hexdigest()[:8]
