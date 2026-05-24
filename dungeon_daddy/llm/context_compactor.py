"""Trim context docs to a token budget while preserving section headings."""
from __future__ import annotations

import re
from typing import Callable


def _default_count_tokens(text: str) -> int:
    return len(text) // 4


class ContextCompactor:
    def __init__(self, count_tokens: Callable[[str], int] | None = None):
        self._count_tokens = count_tokens or _default_count_tokens

    def compact(self, text: str, max_tokens: int = 800) -> str:
        if self._count_tokens(text) <= max_tokens:
            return text
        return self._trim(text, max_tokens)

    def _trim(self, text: str, max_tokens: int) -> str:
        sections = _parse_sections(text)

        heading_tokens = sum(
            self._count_tokens(s["heading"]) for s in sections if s["heading"]
        )
        body_budget = max(0, max_tokens - heading_tokens)

        parts: list[str] = []
        for section in sections:
            if section["heading"]:
                parts.append(section["heading"])
            if section["body"] and body_budget > 0:
                trimmed = _trim_to_budget(section["body"], body_budget, self._count_tokens)
                body_budget -= self._count_tokens(trimmed)
                if trimmed:
                    parts.append(trimmed)

        return "\n".join(parts).rstrip()


def _parse_sections(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(^#+[^\n]*)", text, flags=re.MULTILINE)
    sections: list[dict[str, str]] = []

    if parts[0].strip():
        sections.append({"heading": "", "body": parts[0].strip()})

    i = 1
    while i < len(parts):
        heading = parts[i]
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append({"heading": heading, "body": body})
        i += 2

    return sections


def _trim_to_budget(text: str, max_tokens: int, count_tokens: Callable[[str], int]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    for sentence in sentences:
        candidate = " ".join(kept + [sentence]) if kept else sentence
        if count_tokens(candidate) > max_tokens:
            break
        kept.append(sentence)
    return " ".join(kept)
