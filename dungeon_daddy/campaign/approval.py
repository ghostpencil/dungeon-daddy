from __future__ import annotations

import sys
from typing import TextIO

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.patch import ManifestPatch
from dungeon_daddy.campaign.validator import ManifestError


def format_patch_diff(manifest: CampaignManifest, patch: ManifestPatch) -> str:
    lines: list[str] = []

    for actor in patch.add_actors:
        lines.append(f"  + actor: {actor.slug!r} ({actor.display_name}) [{actor.actor_type}]")
    for slug in patch.remove_actor_slugs:
        lines.append(f"  - actor: {slug!r}")
    for clock in patch.add_clocks:
        lines.append(f"  + clock: {clock.slug!r} ({clock.label}, {clock.segments} segments)")
    for slug in patch.remove_clock_slugs:
        lines.append(f"  - clock: {slug!r}")
    for threat in patch.add_room_threats:
        lines.append(f"  + room_threat: location={threat.get('location_slug')!r}")
    for loc in patch.remove_room_threat_locations:
        lines.append(f"  - room_threat: location={loc!r}")
    for seed in patch.add_memory_seeds:
        lines.append(f"  + memory_seed: {seed!r}")
    for seed in patch.remove_memory_seeds:
        lines.append(f"  - memory_seed: {seed!r}")

    if not lines:
        return "(no changes)"
    return "\n".join(lines)


def run_approval_flow(
    manifest: CampaignManifest,
    patch: ManifestPatch,
    errors: list[ManifestError],
    *,
    out: TextIO = sys.stdout,
    inp: TextIO = sys.stdin,
) -> bool:
    if patch.rationale:
        out.write(f"Rationale: {patch.rationale}\n\n")

    out.write("Proposed changes:\n")
    out.write(format_patch_diff(manifest, patch))
    out.write("\n")

    if errors:
        out.write(f"\nValidation errors ({len(errors)}):\n")
        for err in errors:
            out.write(f"  {err.field}: {err.message}\n")
        out.write("\nPatch rejected — validation failed.\n")
        return False

    out.write("\nApply this patch? [y/N] ")
    answer = inp.readline().strip().lower()
    return answer == "y"
