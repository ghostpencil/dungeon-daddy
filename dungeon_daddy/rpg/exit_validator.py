from __future__ import annotations

from dungeon_daddy.rpg.models import RoomExit


def validate_exit_conditions(
    exit_obj: RoomExit,
    inventory_slugs: list[str],
    room_objects: list[dict],
    clocks: list[dict],
    approved_memory_slugs: list[str],
) -> dict | None:
    """Check all conditions on an exit. Returns None on pass or a structured failure dict."""
    if exit_obj.requires_item_slug is not None:
        if exit_obj.requires_item_slug not in inventory_slugs:
            return {
                "reason": "locked",
                "missing": exit_obj.requires_item_slug,
                "label": exit_obj.label,
            }

    if exit_obj.requires_object_id is not None and exit_obj.requires_object_state is not None:
        obj = next((o for o in room_objects if o["object_id"] == exit_obj.requires_object_id), None)
        if obj is None or obj["current_state"] != exit_obj.requires_object_state:
            return {
                "reason": "locked",
                "missing": exit_obj.requires_object_id,
                "label": exit_obj.label,
            }

    if exit_obj.requires_clock_slug is not None:
        slug = exit_obj.requires_clock_slug
        clock = next((c for c in clocks if c["clock_id"].endswith(f":{slug}")), None)
        min_filled = exit_obj.requires_clock_min_filled or 0
        if clock is None or (clock["status"] != "completed" and clock["filled"] < min_filled):
            return {
                "reason": "locked",
                "missing": slug,
                "label": exit_obj.label,
            }

    if exit_obj.requires_memory_slug is not None:
        if exit_obj.requires_memory_slug not in approved_memory_slugs:
            return {
                "reason": "locked",
                "missing": exit_obj.requires_memory_slug,
                "label": exit_obj.label,
            }

    return None
