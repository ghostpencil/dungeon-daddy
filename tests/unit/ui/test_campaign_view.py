"""Unit tests for CampaignView state machine — Phase 42."""
from __future__ import annotations

import pytest

from dungeon_daddy.campaign.manifest import (
    ActorManifest,
    CampaignManifest,
    ClockManifest,
    FactionManifest,
)

from dungeon_daddy.views.campaign_view import CampaignView


def _make_view() -> CampaignView:
    """Construct CampaignView without arcade initialisation."""
    view = CampaignView.__new__(CampaignView)
    view._init_state()
    return view


def _minimal_manifest() -> CampaignManifest:
    return CampaignManifest(
        slug="test-campaign",
        title="Test Campaign",
        dungeon_slug="test-dungeon",
        player_side=[],
        world_actors=[],
        factions=[],
        clocks=[],
        memory_seeds=[],
        room_threats=[],
    )


# ---------------------------------------------------------------------------
# Slice 1 — initial state
# ---------------------------------------------------------------------------


def test_initial_state_no_manifest():
    view = _make_view()
    assert view.manifest is None
    assert view.active_section is None
    assert view.is_dirty is False


# ---------------------------------------------------------------------------
# Slice 2 — load_manifest
# ---------------------------------------------------------------------------


def test_load_manifest_sets_manifest():
    view = _make_view()
    m = _minimal_manifest()
    view.load_manifest(m)
    assert view.manifest is m


def test_load_manifest_clears_dirty():
    view = _make_view()
    view.is_dirty = True
    view.load_manifest(_minimal_manifest())
    assert view.is_dirty is False


def test_load_manifest_auto_selects_first_section():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    assert view.active_section == "player_side"


# ---------------------------------------------------------------------------
# Slice 3 — set_active_section
# ---------------------------------------------------------------------------


def test_set_active_section_changes_section():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_active_section("clocks")
    assert view.active_section == "clocks"


# ---------------------------------------------------------------------------
# Slice 2 — Actor CRUD
# ---------------------------------------------------------------------------


def _make_actor(slug: str = "valeria", actor_type: str = "pc") -> ActorManifest:
    return ActorManifest(slug=slug, display_name=slug.title(), actor_type=actor_type)


def test_add_actor_appends_to_world_actors():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    actor = _make_actor("valeria", "pc")
    view.add_actor(actor)
    assert actor in view.manifest.world_actors


def test_add_faction_actor_appends_to_factions():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    faction = FactionManifest(slug="iron-guild", display_name="Iron Guild")
    view.add_actor(faction)
    assert faction in view.manifest.factions
    assert faction not in view.manifest.world_actors


def test_add_actor_sets_dirty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_actor(_make_actor())
    assert view.is_dirty is True


def test_update_actor_patches_field_in_world_actors():
    view = _make_view()
    m = _minimal_manifest()
    m.world_actors.append(_make_actor("valeria", "pc"))
    view.load_manifest(m)
    view.update_actor("valeria", display_name="Lady Valeria")
    assert view.manifest.world_actors[0].display_name == "Lady Valeria"


def test_update_actor_patches_field_in_factions():
    view = _make_view()
    m = _minimal_manifest()
    m.factions.append(FactionManifest(slug="iron-guild", display_name="Iron Guild"))
    view.load_manifest(m)
    view.update_actor("iron-guild", display_name="The Iron Guild")
    assert view.manifest.factions[0].display_name == "The Iron Guild"


def test_update_actor_sets_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.world_actors.append(_make_actor("valeria", "pc"))
    view.load_manifest(m)
    view.update_actor("valeria", display_name="X")
    assert view.is_dirty is True


def test_remove_actor_removes_from_world_actors():
    view = _make_view()
    m = _minimal_manifest()
    m.world_actors.append(_make_actor("valeria", "pc"))
    view.load_manifest(m)
    view.remove_actor("valeria")
    assert all(a.slug != "valeria" for a in view.manifest.world_actors)


def test_remove_actor_removes_from_factions():
    view = _make_view()
    m = _minimal_manifest()
    m.factions.append(FactionManifest(slug="iron-guild", display_name="Iron Guild"))
    view.load_manifest(m)
    view.remove_actor("iron-guild")
    assert all(a.slug != "iron-guild" for a in view.manifest.factions)


def test_remove_actor_sets_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.world_actors.append(_make_actor("valeria", "pc"))
    view.load_manifest(m)
    view.remove_actor("valeria")
    assert view.is_dirty is True


def test_set_player_side_updates_manifest():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_player_side(["slug-a", "slug-b"])
    assert view.manifest.player_side == ["slug-a", "slug-b"]


def test_set_player_side_sets_dirty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_player_side(["slug-a"])
    assert view.is_dirty is True


# ---------------------------------------------------------------------------
# Slice 3 — Clock CRUD
# ---------------------------------------------------------------------------


def _make_clock(slug: str = "doom-clock") -> ClockManifest:
    return ClockManifest(slug=slug, label=slug.replace("-", " ").title(), segments=6)


def test_add_clock_appends_to_clocks():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    clock = _make_clock()
    view.add_clock(clock)
    assert clock in view.manifest.clocks


def test_add_clock_sets_dirty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_clock(_make_clock())
    assert view.is_dirty is True


def test_update_clock_patches_field():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock("doom-clock"))
    view.load_manifest(m)
    view.update_clock("doom-clock", filled=3)
    assert view.manifest.clocks[0].filled == 3


def test_update_clock_sets_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock("doom-clock"))
    view.load_manifest(m)
    view.update_clock("doom-clock", filled=1)
    assert view.is_dirty is True


def test_remove_clock_removes_from_clocks():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock("doom-clock"))
    view.load_manifest(m)
    view.remove_clock("doom-clock")
    assert all(c.slug != "doom-clock" for c in view.manifest.clocks)


def test_remove_clock_sets_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock("doom-clock"))
    view.load_manifest(m)
    view.remove_clock("doom-clock")
    assert view.is_dirty is True


# ---------------------------------------------------------------------------
# Slice 4 — Memory seed & room threat CRUD
# ---------------------------------------------------------------------------


def test_add_memory_seed_appends_text():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_memory_seed("The cathedral was built on cursed ground.")
    assert "The cathedral was built on cursed ground." in view.manifest.memory_seeds


def test_add_memory_seed_sets_dirty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_memory_seed("A dark secret.")
    assert view.is_dirty is True


def test_remove_memory_seed_removes_by_index():
    view = _make_view()
    m = _minimal_manifest()
    m.memory_seeds = ["seed-one", "seed-two", "seed-three"]
    view.load_manifest(m)
    view.remove_memory_seed(1)
    assert view.manifest.memory_seeds == ["seed-one", "seed-three"]


def test_remove_memory_seed_sets_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.memory_seeds = ["seed-one"]
    view.load_manifest(m)
    view.remove_memory_seed(0)
    assert view.is_dirty is True


def test_add_room_threat_appends_threat():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    threat = {"location_slug": "vault-b", "description": "Crumbling floor."}
    view.add_room_threat(threat)
    assert threat in view.manifest.room_threats


def test_add_room_threat_sets_dirty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_room_threat({"location_slug": "vault-b", "description": "Trap."})
    assert view.is_dirty is True


def test_remove_room_threat_removes_by_index():
    view = _make_view()
    m = _minimal_manifest()
    m.room_threats = [
        {"location_slug": "hall-a", "description": "Spikes."},
        {"location_slug": "vault-b", "description": "Pit."},
        {"location_slug": "crypt-c", "description": "Gas."},
    ]
    view.load_manifest(m)
    view.remove_room_threat(1)
    assert len(view.manifest.room_threats) == 2
    assert all(t["location_slug"] != "vault-b" for t in view.manifest.room_threats)


def test_remove_room_threat_sets_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.room_threats = [{"location_slug": "hall-a", "description": "Spikes."}]
    view.load_manifest(m)
    view.remove_room_threat(0)
    assert view.is_dirty is True


# ---------------------------------------------------------------------------
# Slice 5 — Validation
# ---------------------------------------------------------------------------


def test_run_validation_clean_manifest_returns_empty():
    view = _make_view()
    m = _minimal_manifest()
    actor = _make_actor("valeria", "pc")
    m.world_actors.append(actor)
    m.player_side = ["valeria"]
    view.load_manifest(m)
    errors = view.run_validation()
    assert errors == []
    assert view._validation_result == []


def test_run_validation_invalid_manifest_returns_errors():
    view = _make_view()
    m = _minimal_manifest()
    # player_side is empty → validator will flag it
    view.load_manifest(m)
    errors = view.run_validation()
    assert len(errors) > 0
    assert view._validation_result is errors


def test_run_validation_stores_result_for_later_retrieval():
    view = _make_view()
    m = _minimal_manifest()
    view.load_manifest(m)
    view.run_validation()
    assert view._validation_result is not None


# ---------------------------------------------------------------------------
# Slice 6 — Save/load
# ---------------------------------------------------------------------------


def test_save_to_path_writes_valid_json(tmp_path):
    view = _make_view()
    m = _minimal_manifest()
    view.load_manifest(m)
    dest = tmp_path / "campaign.json"
    view.save_to_path(dest)
    assert dest.exists()
    import json
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["slug"] == "test-campaign"


def test_save_to_path_json_is_readable_as_manifest(tmp_path):
    from dungeon_daddy.campaign.manifest import CampaignManifest
    view = _make_view()
    m = _minimal_manifest()
    view.load_manifest(m)
    dest = tmp_path / "campaign.json"
    view.save_to_path(dest)
    import json
    data = json.loads(dest.read_text(encoding="utf-8"))
    reloaded = CampaignManifest(**data)
    assert reloaded.slug == m.slug


def test_save_to_path_clears_dirty(tmp_path):
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.is_dirty = True
    view.save_to_path(tmp_path / "campaign.json")
    assert view.is_dirty is False


def test_load_from_path_sets_manifest(tmp_path):
    view = _make_view()
    m = _minimal_manifest()
    view.load_manifest(m)
    dest = tmp_path / "campaign.json"
    view.save_to_path(dest)

    view2 = _make_view()
    view2.load_from_path(dest)
    assert view2.manifest is not None
    assert view2.manifest.slug == "test-campaign"


def test_load_from_path_clears_dirty(tmp_path):
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    dest = tmp_path / "campaign.json"
    view.save_to_path(dest)

    view2 = _make_view()
    view2.is_dirty = True
    view2.load_from_path(dest)
    assert view2.is_dirty is False


def test_load_from_path_auto_selects_first_section(tmp_path):
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    dest = tmp_path / "campaign.json"
    view.save_to_path(dest)

    view2 = _make_view()
    view2.load_from_path(dest)
    assert view2.active_section == "player_side"


# ---------------------------------------------------------------------------
# _section_counts
# ---------------------------------------------------------------------------


def test_section_counts_empty_when_no_manifest():
    view = _make_view()
    assert view._section_counts() == {}


def test_section_counts_actors_split_by_type():
    view = _make_view()
    m = _minimal_manifest()
    pc = _make_actor("valeria", "pc")
    m.world_actors.append(pc)
    m.player_side = ["valeria"]
    m.world_actors.append(_make_actor("troll", "monster"))
    m.world_actors.append(_make_actor("innkeeper", "npc"))
    view.load_manifest(m)
    counts = view._section_counts()
    assert counts["player_side"] == 1
    assert counts["monsters"] == 1
    assert counts["npcs"] == 1


def test_section_counts_clocks_lore_threats():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock())
    m.clocks.append(_make_clock("doom-2"))
    m.memory_seeds = ["seed-a", "seed-b"]
    m.room_threats = [{"location_slug": "hall-a", "description": "trap"}]
    view.load_manifest(m)
    counts = view._section_counts()
    assert counts["clocks"] == 2
    assert counts["lore"] == 2
    assert counts["threats"] == 1


# ---------------------------------------------------------------------------
# _section_items
# ---------------------------------------------------------------------------


def test_section_items_empty_when_no_manifest():
    view = _make_view()
    assert view._section_items() == []


def test_section_items_player_side_filters_by_slug():
    view = _make_view()
    m = _minimal_manifest()
    pc = _make_actor("valeria", "pc")
    npc = _make_actor("troll", "npc")
    m.world_actors = [pc, npc]
    m.player_side = ["valeria"]
    view.load_manifest(m)
    view.set_active_section("player_side")
    items = view._section_items()
    assert len(items) == 1
    assert items[0].slug == "valeria"


def test_section_items_monsters_filters_by_actor_type():
    view = _make_view()
    m = _minimal_manifest()
    m.world_actors = [_make_actor("troll", "monster"), _make_actor("valeria", "pc")]
    view.load_manifest(m)
    view.set_active_section("monsters")
    items = view._section_items()
    assert len(items) == 1
    assert items[0].slug == "troll"


def test_section_items_clocks():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock())
    view.load_manifest(m)
    view.set_active_section("clocks")
    assert len(view._section_items()) == 1


def test_section_items_lore():
    view = _make_view()
    m = _minimal_manifest()
    m.memory_seeds = ["lore-a", "lore-b"]
    view.load_manifest(m)
    view.set_active_section("lore")
    items = view._section_items()
    assert items == ["lore-a", "lore-b"]


def test_section_items_validation_returns_results_when_run():
    view = _make_view()
    m = _minimal_manifest()  # no player_side → will fail validation
    view.load_manifest(m)
    view.run_validation()
    view.set_active_section("validation")
    items = view._section_items()
    assert len(items) > 0


# ---------------------------------------------------------------------------
# _parse_stress_keys — stress track form field extraction
# ---------------------------------------------------------------------------


def test_parse_stress_keys_extracts_track_capacity():
    from dungeon_daddy.views.campaign_view import _parse_stress_keys
    data = {"display_name": "Valeria", "stress_body": "6", "stress_composure": "8"}
    result = _parse_stress_keys(data, [])
    keys = {t["track_key"] for t in result}
    assert "body" in keys
    assert "composure" in keys
    body = next(t for t in result if t["track_key"] == "body")
    assert body["capacity"] == 6
    assert body["filled"] == 0


def test_parse_stress_keys_preserves_existing_filled():
    from dungeon_daddy.views.campaign_view import _parse_stress_keys
    existing = [{"track_key": "body", "capacity": 6, "filled": 3}]
    data = {"stress_body": "6"}
    result = _parse_stress_keys(data, existing)
    body = next(t for t in result if t["track_key"] == "body")
    assert body["filled"] == 3


def test_parse_stress_keys_ignores_non_stress_keys():
    from dungeon_daddy.views.campaign_view import _parse_stress_keys
    data = {"display_name": "X", "slug": "x", "stress_body": "6"}
    result = _parse_stress_keys(data, [])
    assert len(result) == 1
    assert result[0]["track_key"] == "body"


# ---------------------------------------------------------------------------
# _parse_rating_keys — action ratings form field extraction
# ---------------------------------------------------------------------------


def test_parse_rating_keys_extracts_nonzero_ratings():
    from dungeon_daddy.views.campaign_view import _parse_rating_keys
    data = {"rating_fight": "2", "rating_move": "1", "rating_sway": "0", "display_name": "X"}
    result = _parse_rating_keys(data)
    assert result == {"fight": 2, "move": 1}


def test_parse_rating_keys_excludes_zeros():
    from dungeon_daddy.views.campaign_view import _parse_rating_keys
    data = {"rating_fight": "0", "rating_move": "0"}
    result = _parse_rating_keys(data)
    assert result == {}


def test_parse_rating_keys_ignores_non_rating_keys():
    from dungeon_daddy.views.campaign_view import _parse_rating_keys
    data = {"display_name": "X", "slug": "x", "rating_fight": "2"}
    result = _parse_rating_keys(data)
    assert "display_name" not in result
    assert result == {"fight": 2}
