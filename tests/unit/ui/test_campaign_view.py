"""Unit tests for CampaignView state machine — Phase 42."""
from __future__ import annotations

import pytest

from dungeon_daddy.campaign.manifest import (
    ActorManifest,
    CampaignManifest,
    ClockManifest,
    FactionManifest,
    RoomObjectManifest,
)
from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room

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


# Mutators that should flip the dirty flag — merged from the individual
# *_sets_dirty tests. Each case: (populate manifest, mutate view). Helpers
# referenced inside the lambdas (_make_clock) are resolved at call time.
_DIRTY_MUTATIONS = [
    (lambda m: None, lambda v: v.add_actor(_make_actor())),
    (
        lambda m: m.world_actors.append(_make_actor("valeria", "pc")),
        lambda v: v.update_actor("valeria", display_name="X"),
    ),
    (
        lambda m: m.world_actors.append(_make_actor("valeria", "pc")),
        lambda v: v.remove_actor("valeria"),
    ),
    (lambda m: None, lambda v: v.set_player_side(["slug-a"])),
    (lambda m: None, lambda v: v.add_clock(_make_clock())),
    (
        lambda m: m.clocks.append(_make_clock("doom-clock")),
        lambda v: v.update_clock("doom-clock", filled=1),
    ),
    (
        lambda m: m.clocks.append(_make_clock("doom-clock")),
        lambda v: v.remove_clock("doom-clock"),
    ),
    (lambda m: None, lambda v: v.add_memory_seed("A dark secret.")),
    (
        lambda m: setattr(m, "memory_seeds", ["seed-one"]),
        lambda v: v.remove_memory_seed(0),
    ),
    (
        lambda m: None,
        lambda v: v.add_room_threat(
            {"location_slug": "vault-b", "description": "Trap."}
        ),
    ),
    (
        lambda m: setattr(
            m, "room_threats", [{"location_slug": "hall-a", "description": "Spikes."}]
        ),
        lambda v: v.remove_room_threat(0),
    ),
    (lambda m: None, lambda v: v.attach_dungeon("bone-cathedral")),
]


@pytest.mark.parametrize("populate,mutate", _DIRTY_MUTATIONS)
def test_mutation_sets_dirty(populate, mutate):
    view = _make_view()
    m = _minimal_manifest()
    populate(m)
    view.load_manifest(m)
    mutate(view)
    assert view.is_dirty is True


_ACTOR_COLLECTION_CASES = [
    (
        lambda m: m.world_actors.append(_make_actor("valeria", "pc")),
        "valeria",
        "world_actors",
    ),
    (
        lambda m: m.factions.append(
            FactionManifest(slug="iron-guild", display_name="Iron Guild")
        ),
        "iron-guild",
        "factions",
    ),
]


@pytest.mark.parametrize("populate,slug,collection", _ACTOR_COLLECTION_CASES)
def test_update_actor_patches_field(populate, slug, collection):
    view = _make_view()
    m = _minimal_manifest()
    populate(m)
    view.load_manifest(m)
    view.update_actor(slug, display_name="Renamed")
    assert getattr(view.manifest, collection)[0].display_name == "Renamed"


@pytest.mark.parametrize("populate,slug,collection", _ACTOR_COLLECTION_CASES)
def test_remove_actor_removes_from_collection(populate, slug, collection):
    view = _make_view()
    m = _minimal_manifest()
    populate(m)
    view.load_manifest(m)
    view.remove_actor(slug)
    assert all(a.slug != slug for a in getattr(view.manifest, collection))


def test_set_player_side_updates_manifest():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_player_side(["slug-a", "slug-b"])
    assert view.manifest.player_side == ["slug-a", "slug-b"]


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


def test_update_clock_patches_field():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock("doom-clock"))
    view.load_manifest(m)
    view.update_clock("doom-clock", filled=3)
    assert view.manifest.clocks[0].filled == 3


def test_remove_clock_removes_from_clocks():
    view = _make_view()
    m = _minimal_manifest()
    m.clocks.append(_make_clock("doom-clock"))
    view.load_manifest(m)
    view.remove_clock("doom-clock")
    assert all(c.slug != "doom-clock" for c in view.manifest.clocks)


# ---------------------------------------------------------------------------
# Slice 4 — Memory seed & room threat CRUD
# ---------------------------------------------------------------------------


def test_add_memory_seed_appends_text():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_memory_seed("The cathedral was built on cursed ground.")
    assert "The cathedral was built on cursed ground." in view.manifest.memory_seeds


def test_remove_memory_seed_removes_by_index():
    view = _make_view()
    m = _minimal_manifest()
    m.memory_seeds = ["seed-one", "seed-two", "seed-three"]
    view.load_manifest(m)
    view.remove_memory_seed(1)
    assert view.manifest.memory_seeds == ["seed-one", "seed-three"]


def test_add_room_threat_appends_threat():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    threat = {"location_slug": "vault-b", "description": "Crumbling floor."}
    view.add_room_threat(threat)
    assert threat in view.manifest.room_threats


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


# ---------------------------------------------------------------------------
# Slice 3 (Phase 45) — Attach dungeon + seed persistence
# ---------------------------------------------------------------------------


def test_attach_dungeon_sets_dungeon_slug():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.attach_dungeon("bone-cathedral")
    assert view.manifest.dungeon_slug == "bone-cathedral"


def test_attached_dungeon_slug_returns_slug_after_attach():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.attach_dungeon("bone-cathedral")
    assert view.attached_dungeon_slug == "bone-cathedral"


def test_attached_dungeon_slug_is_none_when_no_manifest():
    view = _make_view()
    assert view.attached_dungeon_slug is None


def test_attached_dungeon_slug_reflects_manifest_field():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    # _minimal_manifest() sets dungeon_slug="test-dungeon"
    assert view.attached_dungeon_slug == "test-dungeon"


def test_save_seed_writes_to_seed_library(tmp_path):
    from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
    lib = CampaignSeedLibrary(tmp_path)
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_seed_library(lib)
    view.save_seed()
    assert lib.exists("test-campaign")


def test_save_seed_clears_dirty(tmp_path):
    from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
    lib = CampaignSeedLibrary(tmp_path)
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_seed_library(lib)
    view.is_dirty = True
    view.save_seed()
    assert view.is_dirty is False


def test_load_seed_restores_manifest_fields(tmp_path):
    from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
    lib = CampaignSeedLibrary(tmp_path)
    m = _minimal_manifest()
    m.dungeon_slug = "bone-cathedral"
    lib.save(m)

    view = _make_view()
    view.set_seed_library(lib)
    view.load_seed("test-campaign")
    assert view.manifest.slug == "test-campaign"
    assert view.manifest.dungeon_slug == "bone-cathedral"


def test_save_and_load_seed_round_trip(tmp_path):
    from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary
    lib = CampaignSeedLibrary(tmp_path)
    view = _make_view()
    view.set_seed_library(lib)
    view.load_manifest(_minimal_manifest())
    view.attach_dungeon("bone-cathedral")
    view.save_seed()

    view2 = _make_view()
    view2.set_seed_library(lib)
    view2.load_seed("test-campaign")
    assert view2.manifest.dungeon_slug == "bone-cathedral"
    assert view2.manifest.title == "Test Campaign"
    assert view2.is_dirty is False


# ---------------------------------------------------------------------------
# Slice 9 — Rooms section + room object CRUD
# ---------------------------------------------------------------------------


def _minimal_dungeon() -> Dungeon:
    room = Room(id="room-01", num=1, name="Entry Hall", x=0, y=0, w=10, h=10, type="room", note="")
    level = Level(
        id=1, name="Level 1", summary="", ecology="", loop="",
        width=100, height=100, entries=[], rooms=[room], connections=[],
    )
    return Dungeon(
        meta=DungeonMeta(title="Test Dungeon", theme="", setting="", party="", quest=""),
        levels=[level],
    )


def _make_room_object_v(slug: str = "iron-chest", room_id: str = "room-01") -> RoomObjectManifest:
    return RoomObjectManifest(
        slug=slug,
        display_name=slug.replace("-", " ").title(),
        room_id=room_id,
        level_id="level-01",
        archetype="container",
        description="A sturdy chest.",
        initial_state="sealed",
    )


def test_rooms_in_campaign_sections():
    assert "rooms" in CampaignView._SECTIONS


def test_set_dungeon_stores_dungeon():
    view = _make_view()
    dungeon = _minimal_dungeon()
    view.set_dungeon(dungeon)
    assert view._dungeon is dungeon


def test_set_selected_room_updates_state():
    view = _make_view()
    view.set_selected_room("room-01")
    assert view._selected_room_id == "room-01"


def test_set_selected_room_none_clears_selection():
    view = _make_view()
    view.set_selected_room("room-01")
    view.set_selected_room(None)
    assert view._selected_room_id is None


def test_add_room_object_appends_to_manifest():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    obj = _make_room_object_v()
    view.add_room_object(obj)
    assert obj in view.manifest.room_objects


def test_add_room_object_marks_dirty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.add_room_object(_make_room_object_v())
    assert view.is_dirty


def test_remove_room_object_removes_by_slug():
    view = _make_view()
    m = _minimal_manifest()
    obj = _make_room_object_v(slug="iron-chest")
    m.room_objects.append(obj)
    view.load_manifest(m)
    view.remove_room_object("iron-chest")
    assert all(o.slug != "iron-chest" for o in view.manifest.room_objects)


def test_remove_room_object_marks_dirty():
    view = _make_view()
    m = _minimal_manifest()
    m.room_objects.append(_make_room_object_v(slug="iron-chest"))
    view.load_manifest(m)
    view.remove_room_object("iron-chest")
    assert view.is_dirty


def test_section_items_rooms_no_dungeon_returns_empty():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_active_section("rooms")
    assert view._section_items() == []


def test_section_items_rooms_no_room_selected_returns_dungeon_rooms():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    items = view._section_items()
    assert len(items) == 1
    assert items[0].id == "room-01"


def test_section_items_rooms_room_selected_returns_objects():
    view = _make_view()
    m = _minimal_manifest()
    obj = _make_room_object_v(slug="iron-chest", room_id="room-01")
    m.room_objects.append(obj)
    view.load_manifest(m)
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    items = view._section_items()
    assert obj in items


def test_section_items_rooms_filters_objects_by_room():
    view = _make_view()
    m = _minimal_manifest()
    obj1 = _make_room_object_v(slug="obj-1", room_id="room-01")
    obj2 = _make_room_object_v(slug="obj-2", room_id="room-02")
    m.room_objects.extend([obj1, obj2])
    view.load_manifest(m)
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    items = view._section_items()
    assert obj1 in items
    assert obj2 not in items


def test_section_counts_rooms_top_level_counts_dungeon_rooms():
    # At the top level (no room drilled into) the badge reflects the number of
    # dungeon rooms shown, not the number of placed room objects.
    view = _make_view()
    m = _minimal_manifest()
    m.room_objects.append(_make_room_object_v())
    view.load_manifest(m)
    view.set_dungeon(_minimal_dungeon())
    counts = view._section_counts()
    assert "rooms" in counts
    assert counts["rooms"] == 1  # one dungeon room


def test_section_counts_rooms_top_level_no_dungeon_is_zero():
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    counts = view._section_counts()
    assert counts["rooms"] == 0


def test_section_counts_rooms_when_room_selected_counts_objects():
    view = _make_view()
    m = _minimal_manifest()
    m.room_objects.append(_make_room_object_v(slug="iron-chest", room_id="room-01"))
    m.room_objects.append(_make_room_object_v(slug="oak-door", room_id="room-02"))
    view.load_manifest(m)
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    counts = view._section_counts()
    assert counts["rooms"] == 1  # only objects in room-01


def test_select_room_drills_into_room():
    from unittest.mock import MagicMock
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view._edit_panel = MagicMock()
    view._select_item_at(0)
    assert view._selected_room_id == "room-01"


def test_select_room_object_opens_edit_form():
    from unittest.mock import MagicMock
    view = _make_view()
    m = _minimal_manifest()
    obj = _make_room_object_v(slug="iron-chest", room_id="room-01")
    m.room_objects.append(obj)
    view.load_manifest(m)
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view._edit_panel = MagicMock()
    view._select_item_at(0)
    view._edit_panel.show_room_object.assert_called_once()


# ---------------------------------------------------------------------------
# Phase 47 rooms drill-down — add / save / delete / back navigation fixes
# ---------------------------------------------------------------------------


def test_start_new_item_rooms_with_room_selected_opens_new_form():
    from unittest.mock import MagicMock
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view._edit_panel = MagicMock()
    view._start_new_item()
    view._edit_panel.show_room_object.assert_called_once()
    args, kwargs = view._edit_panel.show_room_object.call_args
    blank = args[0]
    assert blank.room_id == "room-01"
    assert blank.level_id == "1"  # derived from dungeon level containing room
    assert kwargs.get("is_new") is True


def test_start_new_item_rooms_no_room_selected_is_noop():
    from unittest.mock import MagicMock
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view._edit_panel = MagicMock()
    view._start_new_item()
    view._edit_panel.show_room_object.assert_not_called()


def test_on_form_save_new_room_object_adds_to_manifest():
    from unittest.mock import MagicMock
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view._edit_panel = MagicMock()
    view._edit_panel.mode = "new_room_object"
    data = {
        "slug": "iron-chest", "display_name": "Iron Chest",
        "room_id": "room-01", "level_id": "1",
        "archetype": "container", "description": "A sturdy chest.",
        "initial_state": "sealed", "transitions": [],
    }
    view._on_form_save(data)
    assert any(o.slug == "iron-chest" for o in view.manifest.room_objects)
    assert view.is_dirty


def test_on_form_save_edit_room_object_updates_fields():
    from unittest.mock import MagicMock
    view = _make_view()
    m = _minimal_manifest()
    m.room_objects.append(_make_room_object_v(slug="iron-chest", room_id="room-01"))
    view.load_manifest(m)
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view._selected_item_index = 0
    view._edit_panel = MagicMock()
    view._edit_panel.mode = "room_object"
    data = {
        "slug": "iron-chest", "display_name": "Rusty Chest",
        "room_id": "room-01", "level_id": "1",
        "archetype": "container", "description": "Now rusty.",
        "initial_state": "sealed", "transitions": [],
    }
    view._on_form_save(data)
    updated = view.manifest.room_objects[0]
    assert updated.display_name == "Rusty Chest"
    assert updated.description == "Now rusty."


def test_delete_item_at_rooms_removes_object():
    from unittest.mock import MagicMock
    view = _make_view()
    m = _minimal_manifest()
    m.room_objects.append(_make_room_object_v(slug="iron-chest", room_id="room-01"))
    view.load_manifest(m)
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view._edit_panel = MagicMock()
    view._delete_item_at(0)
    assert all(o.slug != "iron-chest" for o in view.manifest.room_objects)


def test_back_button_click_deselects_room():
    from unittest.mock import MagicMock
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view.window = MagicMock(width=1400, height=900)
    view._edit_panel = MagicMock()
    nav = MagicMock()
    nav.section_at.return_value = None
    nav.save_btn_at.return_value = False
    view._nav_panel = nav
    lp = MagicMock()
    lp.back_btn_at.return_value = True
    lp.add_btn_at.return_value = False
    lp.delete_zone_at.return_value = None
    lp.item_at.return_value = None
    view._list_panel = lp
    view.on_mouse_press(300, 400, 1, 0)
    assert view._selected_room_id is None


def test_nav_section_click_resets_selected_room():
    from unittest.mock import MagicMock
    view = _make_view()
    view.load_manifest(_minimal_manifest())
    view.set_dungeon(_minimal_dungeon())
    view.set_active_section("rooms")
    view.set_selected_room("room-01")
    view.window = MagicMock(width=1400, height=900)
    view._edit_panel = MagicMock()
    nav = MagicMock()
    nav.section_at.return_value = "monsters"
    view._nav_panel = nav
    view._list_panel = MagicMock()
    view.on_mouse_press(50, 400, 1, 0)
    assert view._selected_room_id is None
    assert view.active_section == "monsters"
