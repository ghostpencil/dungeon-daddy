from __future__ import annotations

import importlib.resources
import json
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

_UNIVERSAL_VERBS = frozenset(
    {"fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"}
)
_VALID_TRACK_KEYS = frozenset({"body", "composure", "bonds", "weird"})
_VALID_TARGET_TYPES = frozenset({"npc", "object", "item", "room", "self", "monster"})


class PlaybookStressTrack(BaseModel):
    track_key: str
    capacity: int = 4

    @field_validator("track_key")
    @classmethod
    def _validate_track_key(cls, v: str) -> str:
        if v not in _VALID_TRACK_KEYS:
            raise ValueError(f"track_key must be one of {sorted(_VALID_TRACK_KEYS)}; got {v!r}")
        return v


class SignatureAdverb(BaseModel):
    slug: str
    target_types: list[str]

    @field_validator("target_types")
    @classmethod
    def _validate_target_types(cls, v: list[str]) -> list[str]:
        bad = set(v) - _VALID_TARGET_TYPES
        if bad:
            raise ValueError(f"Invalid target_types: {sorted(bad)}")
        return v


class PlaybookAbility(BaseModel):
    slug: str
    display_name: str
    description: str
    surfaces_as_verb: bool = False
    target_types: list[str] = []
    cost_type: Literal["none", "active_stress", "momentum"] = "none"
    cost_amount: int = 0


class PlaybookKit(BaseModel):
    slug: str
    display_name: str
    description: str
    charges_max: int
    abilities: list[PlaybookAbility] = []


class Playbook(BaseModel):
    slug: str
    display_name: str
    starting_action_ratings: dict[str, int]
    starting_stress_tracks: list[PlaybookStressTrack]
    starting_kit: PlaybookKit
    tags: list[str]
    signature_adverbs: list[SignatureAdverb]
    starting_abilities: list[str]
    ability_pool: list[PlaybookAbility] = []
    beats: list[dict] = []

    @model_validator(mode="after")
    def _validate_abilities(self) -> "Playbook":
        kit_slugs = [a.slug for a in self.starting_kit.abilities]
        pool_slugs = [a.slug for a in self.ability_pool]
        all_slugs = kit_slugs + pool_slugs
        seen: set[str] = set()
        duplicates: set[str] = set()
        for slug in all_slugs:
            if slug in seen:
                duplicates.add(slug)
            seen.add(slug)
        if duplicates:
            raise ValueError(f"Duplicate ability slugs across kit and pool: {sorted(duplicates)}")
        available = set(all_slugs)
        unknown = set(self.starting_abilities) - available
        if unknown:
            raise ValueError(
                f"starting_abilities slugs not found in kit or pool: {sorted(unknown)}"
            )
        return self

    @field_validator("starting_action_ratings")
    @classmethod
    def _validate_action_ratings(cls, v: dict[str, int]) -> dict[str, int]:
        bad_keys = set(v) - _UNIVERSAL_VERBS
        if bad_keys:
            raise ValueError(f"Unknown action keys: {sorted(bad_keys)}")
        bad_ratings = {k: r for k, r in v.items() if not (0 <= r <= 3)}
        if bad_ratings:
            raise ValueError(f"Ratings must be 0–3; got {bad_ratings}")
        return v


class PlaybookLibrary:
    def __init__(self) -> None:
        pkg = importlib.resources.files("dungeon_daddy.data")
        raw = (pkg / "playbooks.json").read_text(encoding="utf-8")
        entries: list[dict] = json.loads(raw)
        self._playbooks: dict[str, Playbook] = {
            entry["slug"]: Playbook.model_validate(entry) for entry in entries
        }

    def list(self) -> list[Playbook]:
        return list(self._playbooks.values())

    def get(self, slug: str) -> Playbook:
        try:
            return self._playbooks[slug]
        except KeyError:
            raise KeyError(f"No playbook with slug {slug!r}") from None
