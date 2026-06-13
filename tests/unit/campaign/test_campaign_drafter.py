from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from dungeon_daddy.campaign.drafter import CampaignDrafter, DraftError
from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.patch import ManifestPatch


def _base_manifest() -> CampaignManifest:
    return CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        player_side=["valeria"],
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc"),
        ],
        clocks=[
            ClockManifest(slug="final-rite", label="Final Rite Completion", segments=8),
        ],
        memory_seeds=["The party entered through a collapsed side chapel."],
    )


def _mock_provider(response: str = "{}") -> MagicMock:
    provider = MagicMock()
    provider.complete.return_value = response
    return provider


class TestDrafterCallsProvider:
    def test_draft_calls_provider_complete_once(self) -> None:
        provider = _mock_provider()
        drafter = CampaignDrafter(provider)

        drafter.draft(_base_manifest(), "Add an undead jailer to the ossuary.")

        provider.complete.assert_called_once()

    def test_draft_includes_request_in_messages(self) -> None:
        provider = _mock_provider()
        drafter = CampaignDrafter(provider)
        request = "Add an undead jailer to the ossuary."

        drafter.draft(_base_manifest(), request)

        call_kwargs = provider.complete.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        message_contents = [m.content for m in messages]
        assert any(request in content for content in message_contents)


class TestDrafterParsesResponse:
    def test_draft_returns_patch_from_provider_json(self) -> None:
        patch_json = json.dumps({
            "add_actors": [
                {
                    "slug": "undead-jailer",
                    "display_name": "The Undead Jailer",
                    "actor_type": "monster",
                }
            ],
            "rationale": "Adding an undead jailer as requested.",
        })
        provider = _mock_provider(response=patch_json)
        drafter = CampaignDrafter(provider)

        result = drafter.draft(_base_manifest(), "Add an undead jailer to the ossuary.")

        assert isinstance(result, ManifestPatch)
        assert len(result.add_actors) == 1
        assert result.add_actors[0].slug == "undead-jailer"
        assert result.rationale == "Adding an undead jailer as requested."


class TestDrafterErrorHandling:
    def test_invalid_json_raises_draft_error(self) -> None:
        provider = _mock_provider(response="not valid json {{{")
        drafter = CampaignDrafter(provider)

        with pytest.raises(DraftError):
            drafter.draft(_base_manifest(), "Add an undead jailer.")
