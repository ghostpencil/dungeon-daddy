from __future__ import annotations

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.patch import ManifestPatch, apply_patch
from dungeon_daddy.campaign.validator import ManifestError, validate_manifest


def validate_patch(manifest: CampaignManifest, patch: ManifestPatch) -> list[ManifestError]:
    patched = apply_patch(manifest, patch)
    return validate_manifest(patched)
