"""Integration tests for Phase 41.5 — AI-Assisted Campaign Drafting end-to-end."""
from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from dungeon_daddy.campaign.draft_flow import run_draft_flow
from dungeon_daddy.campaign.drafter import CampaignDrafter
from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.validator import validate_manifest
from dungeon_daddy.llm.provider import LLMMessage


# ---------------------------------------------------------------------------
# Stub LLM provider — real class, no network calls
# ---------------------------------------------------------------------------


class _StubProvider:
    def __init__(self, response: str) -> None:
        self._response = response

    def complete(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> str:
        return self._response

    def stream(
        self,
        messages: list[LLMMessage],
        system: str = "",
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        yield self._response

    @property
    def model_id(self) -> str:
        return "stub"

    @property
    def last_usage(self) -> tuple[int, int] | None:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(path: Path, manifest: CampaignManifest) -> None:
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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


# ---------------------------------------------------------------------------
# Cycle 1 — Happy path: approve → manifest updated, re-validates clean
# ---------------------------------------------------------------------------


def test_approved_patch_updates_manifest_and_revalidates(tmp_path: Path) -> None:
    manifest_path = tmp_path / "campaign.json"
    _write_manifest(manifest_path, _base_manifest())

    patch_json = json.dumps({
        "rationale": "Adding an undead jailer to the ossuary.",
        "add_actors": [
            {
                "slug": "undead-jailer",
                "display_name": "The Undead Jailer",
                "actor_type": "monster",
            }
        ],
    })
    drafter = CampaignDrafter(_StubProvider(patch_json))

    exit_code = run_draft_flow(
        manifest_path,
        "Add an undead jailer to the ossuary.",
        drafter,
        out=io.StringIO(),
        inp=io.StringIO("y\n"),
    )

    assert exit_code == 0

    updated = CampaignManifest(**json.loads(manifest_path.read_text(encoding="utf-8")))
    slugs = {a.slug for a in updated.world_actors}
    assert "undead-jailer" in slugs

    errors = validate_manifest(updated)
    assert errors == []


# ---------------------------------------------------------------------------
# Cycle 2 — Validation failure: patch rejected, file unchanged
# ---------------------------------------------------------------------------


def test_invalid_patch_is_rejected_and_file_unchanged(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest_path = tmp_path / "campaign.json"
    _write_manifest(manifest_path, manifest)
    original_text = manifest_path.read_text(encoding="utf-8")

    # Remove the only actor — leaves player_side referencing a missing slug
    patch_json = json.dumps({
        "rationale": "Remove Valeria.",
        "remove_actor_slugs": ["valeria"],
    })
    drafter = CampaignDrafter(_StubProvider(patch_json))

    exit_code = run_draft_flow(
        manifest_path,
        "Remove Valeria from the campaign.",
        drafter,
        out=io.StringIO(),
        inp=io.StringIO("y\n"),
    )

    assert exit_code == 1
    assert manifest_path.read_text(encoding="utf-8") == original_text


# ---------------------------------------------------------------------------
# Cycle 3 — User rejection: valid patch declined, file unchanged
# ---------------------------------------------------------------------------


def test_rejected_patch_leaves_file_unchanged(tmp_path: Path) -> None:
    manifest_path = tmp_path / "campaign.json"
    _write_manifest(manifest_path, _base_manifest())
    original_text = manifest_path.read_text(encoding="utf-8")

    patch_json = json.dumps({
        "rationale": "Adding an undead jailer.",
        "add_actors": [
            {
                "slug": "undead-jailer",
                "display_name": "The Undead Jailer",
                "actor_type": "monster",
            }
        ],
    })
    drafter = CampaignDrafter(_StubProvider(patch_json))

    exit_code = run_draft_flow(
        manifest_path,
        "Add an undead jailer.",
        drafter,
        out=io.StringIO(),
        inp=io.StringIO("n\n"),
    )

    assert exit_code == 1
    assert manifest_path.read_text(encoding="utf-8") == original_text
