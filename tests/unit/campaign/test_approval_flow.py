from __future__ import annotations

import io

from dungeon_daddy.campaign.approval import format_patch_diff, run_approval_flow
from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest
from dungeon_daddy.campaign.patch import ManifestPatch
from dungeon_daddy.campaign.validator import ManifestError


def _base_manifest() -> CampaignManifest:
    return CampaignManifest(
        slug="bone-cathedral",
        title="The Bone Cathedral",
        dungeon_slug="bone-cathedral",
        player_side=["valeria"],
        world_actors=[
            ActorManifest(slug="valeria", display_name="Valeria Crane", actor_type="pc"),
            ActorManifest(slug="bone-warden", display_name="The Bone Warden", actor_type="dungeon"),
        ],
        clocks=[
            ClockManifest(slug="final-rite", label="Final Rite Completion", segments=8),
        ],
        memory_seeds=["The party entered through a collapsed side chapel."],
    )


class TestFormatPatchDiff:
    def test_added_actor_name_appears_in_diff(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(
            add_actors=[
                ActorManifest(slug="undead-jailer", display_name="The Undead Jailer", actor_type="monster"),
            ]
        )

        diff = format_patch_diff(manifest, patch)

        assert "undead-jailer" in diff or "The Undead Jailer" in diff

    def test_removed_actor_slug_appears_in_diff(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(remove_actor_slugs=["bone-warden"])

        diff = format_patch_diff(manifest, patch)

        assert "bone-warden" in diff

    def test_added_clock_appears_in_diff(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(
            add_clocks=[ClockManifest(slug="cult-ritual", label="Cult Ritual", segments=6)]
        )

        diff = format_patch_diff(manifest, patch)

        assert "cult-ritual" in diff

    def test_added_memory_seed_appears_in_diff(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(add_memory_seeds=["A fresh handprint near the reliquary stairs."])

        diff = format_patch_diff(manifest, patch)

        assert "A fresh handprint near the reliquary stairs." in diff

    def test_empty_patch_shows_no_changes_message(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch()

        diff = format_patch_diff(manifest, patch)

        assert "no changes" in diff


class TestRunApprovalFlow:
    def test_validation_errors_reject_without_prompting(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch()
        errors = [ManifestError(field="player_side", message="player_side must not be empty")]
        out = io.StringIO()
        inp = io.StringIO()  # empty — would raise if read

        approved = run_approval_flow(manifest, patch, errors, out=out, inp=inp)

        assert approved is False
        assert inp.read() == ""  # nothing was consumed from input

    def test_user_says_no_returns_false(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(add_memory_seeds=["A new clue."])
        out = io.StringIO()
        inp = io.StringIO("n\n")

        approved = run_approval_flow(manifest, patch, [], out=out, inp=inp)

        assert approved is False

    def test_user_says_yes_returns_true(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(add_memory_seeds=["A new clue."])
        out = io.StringIO()
        inp = io.StringIO("y\n")

        approved = run_approval_flow(manifest, patch, [], out=out, inp=inp)

        assert approved is True

    def test_rationale_is_shown_when_present(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch(rationale="Adding a new clue for the player.")
        out = io.StringIO()
        inp = io.StringIO("n\n")

        run_approval_flow(manifest, patch, [], out=out, inp=inp)

        assert "Adding a new clue for the player." in out.getvalue()

    def test_error_details_are_shown_when_validation_fails(self) -> None:
        manifest = _base_manifest()
        patch = ManifestPatch()
        errors = [ManifestError(field="player_side", message="player_side must not be empty")]
        out = io.StringIO()
        inp = io.StringIO()

        run_approval_flow(manifest, patch, errors, out=out, inp=inp)

        assert "player_side" in out.getvalue()
        assert "player_side must not be empty" in out.getvalue()


class TestRunDraftFlow:
    """Tests for the end-to-end CLI flow function."""

    def _make_stub_drafter(self, patch: ManifestPatch):
        class _StubDrafter:
            def draft(self, manifest: CampaignManifest, request: str) -> ManifestPatch:
                return patch

        return _StubDrafter()

    def test_approved_patch_is_written_to_manifest_file(self, tmp_path) -> None:
        import json
        from dungeon_daddy.campaign.draft_flow import run_draft_flow

        manifest = _base_manifest()
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
        )

        new_actor = ActorManifest(slug="undead-jailer", display_name="Undead Jailer", actor_type="monster")
        patch = ManifestPatch(add_actors=[new_actor])
        drafter = self._make_stub_drafter(patch)

        exit_code = run_draft_flow(
            manifest_path=manifest_path,
            request="Add an undead jailer",
            drafter=drafter,
            out=io.StringIO(),
            inp=io.StringIO("y\n"),
        )

        assert exit_code == 0
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        actor_slugs = [a["slug"] for a in saved["world_actors"]]
        assert "undead-jailer" in actor_slugs

    def test_rejected_patch_leaves_manifest_unchanged(self, tmp_path) -> None:
        import json
        from dungeon_daddy.campaign.draft_flow import run_draft_flow

        manifest = _base_manifest()
        manifest_path = tmp_path / "manifest.json"
        original_text = json.dumps(manifest.model_dump(mode="json"), indent=2)
        manifest_path.write_text(original_text, encoding="utf-8")

        patch = ManifestPatch(add_actors=[ActorManifest(slug="new-npc", display_name="New NPC", actor_type="npc")])
        drafter = self._make_stub_drafter(patch)

        exit_code = run_draft_flow(
            manifest_path=manifest_path,
            request="Add a new NPC",
            drafter=drafter,
            out=io.StringIO(),
            inp=io.StringIO("n\n"),
        )

        assert exit_code == 1
        assert manifest_path.read_text(encoding="utf-8") == original_text

    def test_invalid_patch_exits_nonzero_and_leaves_file_unchanged(self, tmp_path) -> None:
        import json
        from dungeon_daddy.campaign.draft_flow import run_draft_flow

        manifest = _base_manifest()
        manifest_path = tmp_path / "manifest.json"
        original_text = json.dumps(manifest.model_dump(mode="json"), indent=2)
        manifest_path.write_text(original_text, encoding="utf-8")

        # Removing the only player actor breaks player_side validation
        bad_patch = ManifestPatch(remove_actor_slugs=["valeria"])
        drafter = self._make_stub_drafter(bad_patch)

        exit_code = run_draft_flow(
            manifest_path=manifest_path,
            request="Remove the protagonist",
            drafter=drafter,
            out=io.StringIO(),
            inp=io.StringIO("y\n"),  # would approve, but validation blocks it
        )

        assert exit_code == 1
        assert manifest_path.read_text(encoding="utf-8") == original_text
