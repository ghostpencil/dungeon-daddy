from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.campaign.manifest import ActorManifest, CampaignManifest, ClockManifest

_VALID_ACTION_KEYS: frozenset[str] = frozenset(
    ["fight", "move", "tinker", "study", "focus", "sway", "sense", "channel", "endure"]
)
_VALID_STRESS_TRACK_KEYS: frozenset[str] = frozenset(["body", "composure", "bonds", "weird"])


@dataclass
class ManifestError:
    field: str
    message: str


def validate_manifest(manifest: CampaignManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    errors.extend(_check_duplicate_actor_slugs(manifest))
    errors.extend(_check_duplicate_clock_slugs(manifest))
    errors.extend(_check_player_side(manifest))
    for actor in manifest.world_actors + manifest.factions:
        errors.extend(_check_actor_action_ratings(actor))
        errors.extend(_check_actor_stress_tracks(actor))
    for clock in manifest.clocks:
        errors.extend(_check_clock_segments(clock))
    errors.extend(_check_room_threat_references(manifest))
    return errors


def _check_room_threat_references(manifest: CampaignManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    known_actors = {a.slug for a in manifest.world_actors + manifest.factions}
    known_clocks = {c.slug for c in manifest.clocks}
    for threat in manifest.room_threats:
        for slug in threat.get("related_actor_slugs", []):
            if slug not in known_actors:
                errors.append(ManifestError(
                    field="room_threats.related_actor_slugs",
                    message=f"room_threat references unknown actor: {slug!r}",
                ))
        for slug in threat.get("related_clock_slugs", []):
            if slug not in known_clocks:
                errors.append(ManifestError(
                    field="room_threats.related_clock_slugs",
                    message=f"room_threat references unknown clock: {slug!r}",
                ))
    return errors


def _check_actor_stress_tracks(actor: ActorManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    for track in actor.stress_tracks:
        key = track.get("track_key", "") if isinstance(track, dict) else ""
        if key not in _VALID_STRESS_TRACK_KEYS:
            errors.append(ManifestError(
                field=f"world_actors[{actor.slug}].stress_tracks",
                message=f"Invalid stress track key {key!r} in actor {actor.slug!r}",
            ))
    return errors


def _check_actor_action_ratings(actor: ActorManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    for key in actor.action_ratings:
        if key not in _VALID_ACTION_KEYS:
            errors.append(ManifestError(
                field=f"world_actors[{actor.slug}].action_ratings",
                message=f"Invalid action key {key!r} in actor {actor.slug!r}",
            ))
    return errors


def _check_player_side(manifest: CampaignManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    if not manifest.player_side:
        errors.append(ManifestError(field="player_side", message="player_side must not be empty"))
        return errors
    known = {a.slug for a in manifest.world_actors + manifest.factions}
    for slug in manifest.player_side:
        if slug not in known:
            errors.append(ManifestError(
                field="player_side",
                message=f"player_side references unknown actor: {slug!r}",
            ))
    return errors


def _check_clock_segments(clock: ClockManifest) -> list[ManifestError]:
    if clock.segments < 1:
        return [ManifestError(
            field=f"clocks[{clock.slug}].segments",
            message=f"Clock {clock.slug!r} has segments < 1",
        )]
    return []


def _check_duplicate_clock_slugs(manifest: CampaignManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    seen: set[str] = set()
    for clock in manifest.clocks:
        if clock.slug in seen:
            errors.append(ManifestError(
                field="clocks",
                message=f"Duplicate clock slug: {clock.slug!r}",
            ))
        seen.add(clock.slug)
    return errors


def _check_duplicate_actor_slugs(manifest: CampaignManifest) -> list[ManifestError]:
    errors: list[ManifestError] = []
    all_actors = manifest.world_actors + manifest.factions
    seen: set[str] = set()
    for actor in all_actors:
        if actor.slug in seen:
            errors.append(ManifestError(
                field="world_actors/factions",
                message=f"Duplicate actor slug: {actor.slug!r}",
            ))
        seen.add(actor.slug)
    return errors
