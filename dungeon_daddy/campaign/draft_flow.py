from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Protocol, TextIO

from dungeon_daddy.campaign.approval import run_approval_flow
from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.patch import ManifestPatch, apply_patch
from dungeon_daddy.campaign.patch_validator import validate_patch


class _Drafter(Protocol):
    def draft(self, manifest: CampaignManifest, request: str) -> ManifestPatch: ...


def run_draft_flow(
    manifest_path: Path,
    request: str,
    drafter: _Drafter,
    *,
    out: TextIO = sys.stdout,
    inp: TextIO = sys.stdin,
) -> int:
    """Draft a patch, validate, prompt for approval, apply if approved. Returns exit code."""
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = CampaignManifest(**raw)

    patch = drafter.draft(manifest, request)
    errors = validate_patch(manifest, patch)

    approved = run_approval_flow(manifest, patch, errors, out=out, inp=inp)
    if not approved:
        return 1

    patched = apply_patch(manifest, patch)
    manifest_path.write_text(
        json.dumps(patched.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    out.write(f"\nManifest updated: {manifest_path}\n")
    return 0
