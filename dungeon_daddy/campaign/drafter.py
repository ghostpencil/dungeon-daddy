from __future__ import annotations

import json

from pydantic import ValidationError

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.patch import ManifestPatch
from dungeon_daddy.llm.provider import LLMMessage, LLMProvider

_SYSTEM_PROMPT = """\
You are the Dungeon Daddy campaign editor. Given a campaign manifest and a \
natural-language authoring request, produce a JSON object that describes the \
proposed changes.

Respond with ONLY a valid JSON object — no prose, no markdown fences. The JSON \
must match this schema (all fields optional; omit what you do not need):

{
  "rationale": "<one-sentence explanation of the change>",
  "add_actors": [
    {
      "slug": "<kebab-case-id>",
      "display_name": "<human name>",
      "actor_type": "<pc|npc|monster|dungeon|faction|dungeon_presence>",
      "concept": "<optional short description>",
      "status": "active",
      "action_ratings": {"fight": 2, ...},
      "stress_tracks": [{"track_key": "<body|composure|bonds|weird>", ...}],
      "tags": []
    }
  ],
  "remove_actor_slugs": ["<slug>"],
  "add_clocks": [
    {
      "slug": "<kebab-case-id>",
      "label": "<display label>",
      "segments": 6,
      "clock_level": "<room|level|dungeon|quest|character|faction>",
      "stakes": "<optional>",
      "completion_effect": "<optional>"
    }
  ],
  "remove_clock_slugs": ["<slug>"],
  "add_room_threats": [
    {"location_slug": "<room-slug>", "description": "<threat description>"}
  ],
  "remove_room_threat_locations": ["<location_slug>"],
  "add_memory_seeds": ["<seed text>"],
  "remove_memory_seeds": ["<exact seed text to remove>"]
}

Valid action keys: fight, move, tinker, study, focus, sway, sense, channel, endure.
Valid stress track keys: body, composure, bonds, weird.
"""


class DraftError(Exception):
    """Raised when the LLM response cannot be parsed into a ManifestPatch."""


class CampaignDrafter:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def draft(self, manifest: CampaignManifest, request: str) -> ManifestPatch:
        context = self._build_context(manifest)
        messages = [LLMMessage(role="user", content=f"{context}\n\nRequest: {request}")]
        response = self._provider.complete(
            messages=messages,
            system=_SYSTEM_PROMPT,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        try:
            return ManifestPatch.model_validate_json(response)
        except ValidationError as exc:
            raise DraftError(f"LLM response is not a valid ManifestPatch: {exc}") from exc

    def _build_context(self, manifest: CampaignManifest) -> str:
        return "Current manifest:\n" + json.dumps(manifest.model_dump(), indent=2)
