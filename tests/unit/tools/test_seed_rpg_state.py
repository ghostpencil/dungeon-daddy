"""Tests for tools/seed_rpg_state.py — Phase 33/34 campaign seeder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from seed_rpg_state import SeedResult, seed_campaign, seed_campaign_with_pack

from dungeon_daddy.rpg.seed_pack import derive_actor_id


def _make_campaign_dir(tmp_path: Path, name: str = "test-campaign") -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Slice 1 — dry-run creates no .duckdb
# ---------------------------------------------------------------------------


def test_dry_run_creates_no_duckdb(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=True)
    assert not (campaign_dir / "campaign.duckdb").exists()


def test_dry_run_returns_seed_result(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    result = seed_campaign(campaign_dir, dry_run=True)
    assert isinstance(result, SeedResult)


# ---------------------------------------------------------------------------
# Slice 2 — first apply creates expected rows
# ---------------------------------------------------------------------------


def _open_repo(campaign_dir: Path):
    from dungeon_daddy.memory.repository import MemoryRepository
    return MemoryRepository(campaign_dir / "campaign.duckdb")


def test_first_apply_creates_duckdb(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    assert (campaign_dir / "campaign.duckdb").exists()


def test_no_pc_actor_without_seed_pack(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    actor = repo.get_actor(f"actor:{slug}:protagonist")
    repo.close()
    assert actor is None


def test_first_apply_creates_npc_actors(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    npc = repo.get_actor(f"actor:{slug}:dungeon-presence")
    monster = repo.get_actor(f"actor:{slug}:wandering-threat")
    repo.close()
    assert npc is not None and npc["actor_type"] == "dungeon"
    assert monster is not None and monster["actor_type"] == "monster"


def test_no_stress_tracks_without_seed_pack(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    tracks = repo.get_actor_stress_tracks(f"actor:{slug}:protagonist")
    repo.close()
    assert tracks == []


def test_no_action_ratings_without_seed_pack(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    ratings = repo.get_actor_action_ratings(f"actor:{slug}:protagonist")
    repo.close()
    assert ratings == []


def test_first_apply_creates_clocks(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    campaign_id = f"campaign:{slug}"
    clocks = repo.get_clocks(campaign_id)
    repo.close()
    assert len(clocks) >= 2


def test_first_apply_creates_memory_entries(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    campaign_id = f"campaign:{slug}"
    memories = repo.get_memory_entries_by_campaign(campaign_id)
    repo.close()
    assert len(memories) >= 3


def test_first_apply_result_reports_created_count(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    result = seed_campaign(campaign_dir, dry_run=False)
    assert result.created > 0


def test_no_pc_actors_emits_warning(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    result = seed_campaign(campaign_dir, dry_run=False)
    assert any("player-controlled" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Slice 3 — second apply is idempotent (no duplicates)
# ---------------------------------------------------------------------------


def test_second_apply_creates_no_new_rows(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)
    result2 = seed_campaign(campaign_dir, dry_run=False)
    assert result2.created == 0


def test_second_apply_actor_count_unchanged(tmp_path: Path) -> None:
    campaign_dir = _make_campaign_dir(tmp_path)
    seed_campaign(campaign_dir, dry_run=False)

    repo = _open_repo(campaign_dir)
    slug = "test-campaign"
    campaign_id = f"campaign:{slug}"
    after_first = len(repo.get_clocks(campaign_id))
    memories_first = len(repo.get_memory_entries_by_campaign(campaign_id))
    repo.close()

    seed_campaign(campaign_dir, dry_run=False)

    repo2 = _open_repo(campaign_dir)
    after_second = len(repo2.get_clocks(campaign_id))
    memories_second = len(repo2.get_memory_entries_by_campaign(campaign_id))
    repo2.close()

    assert after_second == after_first
    assert memories_second == memories_first


# ---------------------------------------------------------------------------
# Slice 4 — missing folder fails gracefully
# ---------------------------------------------------------------------------


def test_missing_folder_returns_warning(tmp_path: Path) -> None:
    result = seed_campaign(tmp_path / "nonexistent", dry_run=False)
    assert len(result.warnings) == 1
    assert "not found" in result.warnings[0]


def test_missing_folder_creates_no_files(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent"
    seed_campaign(nonexistent, dry_run=False)
    assert not nonexistent.exists()


# ---------------------------------------------------------------------------
# Slice 5 — seed pack integration (34-4)
# ---------------------------------------------------------------------------

_PACK_DATA = {
    "campaign_slug": "test-campaign",
    "player_side": {
        "label": "The Party",
        "actors": [
            {
                "slug": "mara",
                "display_name": "Mara",
                "actor_type": "pc",
                "actions": {"fight": 2, "move": 1},
                "stress_tracks": ["body", "composure"],
            }
        ],
    },
    "dungeon_side": {
        "actors": [
            {
                "slug": "bone-warden",
                "display_name": "The Bone Warden",
                "actor_type": "monster",
            }
        ]
    },
    "clocks": [
        {
            "slug": "bone-warden-stirs",
            "label": "The Bone Warden Stirs",
            "segments": 6,
            "category": "danger",
        }
    ],
    "memories": [
        {
            "title": "The Expedition's Purpose",
            "summary": "The party seeks the Shattered Seal.",
            "type": "campaign_premise",
            "importance": 8,
            "tags": ["thread:main-quest"],
        }
    ],
    "room_threats": [],
}


def _write_pack(tmp_path: Path, data: dict | None = None) -> Path:
    pack_file = tmp_path / "rpg_seed.json"
    pack_file.write_text(json.dumps(data or _PACK_DATA), encoding="utf-8")
    return pack_file


# A real, shipped dungeon model — used as the room-id source of truth for the
# §4.3 seed-time validation gate. Its rooms are ids like "1-A".."3-E".
_TOMB_MODEL = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "samples" / "tomb_of_the_forgotten_king.json"
)


def _write_dungeon(campaign_dir: Path, model_path: Path = _TOMB_MODEL) -> None:
    (campaign_dir / "dungeon.json").write_text(
        model_path.read_text(encoding="utf-8"), encoding="utf-8"
    )


def _pack_with_room_clock(scope_room_id: str) -> dict:
    return {
        **_PACK_DATA,
        "clocks": [
            {"slug": "trap", "label": "Trap", "segments": 4, "category": "danger",
             "clock_level": "room", "scope_room_id": scope_room_id,
             "stakes": "s", "completion_effect": "e"}
        ],
    }


class TestSeedCampaignWithPack:
    def test_dry_run_creates_no_duckdb(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path, dry_run=True)
        assert not (campaign_dir / "campaign.duckdb").exists()

    def test_first_apply_creates_actors(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        result = seed_campaign_with_pack(campaign_dir, pack_path)
        assert result.created > 0
        repo = _open_repo(campaign_dir)
        actors = repo.get_actors_by_campaign("campaign:test-campaign")
        repo.close()
        display_names = {a["display_name"] for a in actors}
        assert "Mara" in display_names
        assert "The Bone Warden" in display_names

    def test_first_apply_creates_clock(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        clocks = repo.get_clocks("campaign:test-campaign")
        repo.close()
        labels = {c["label"] for c in clocks}
        assert "The Bone Warden Stirs" in labels

    def test_first_apply_creates_memory_with_tag(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        entries = repo.get_memory_entries_by_campaign("campaign:test-campaign")
        repo.close()
        assert any(e["title"] == "The Expedition's Purpose" for e in entries)

    def test_second_apply_without_force_skips_existing(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        result2 = seed_campaign_with_pack(campaign_dir, pack_path, force=False)
        assert result2.created == 0
        assert result2.skipped > 0

    def test_second_apply_with_force_updates_existing(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        result2 = seed_campaign_with_pack(campaign_dir, pack_path, force=True)
        assert result2.updated > 0

    def test_missing_folder_returns_warning(self, tmp_path: Path) -> None:
        pack_path = _write_pack(tmp_path)
        result = seed_campaign_with_pack(tmp_path / "nonexistent", pack_path)
        assert len(result.warnings) == 1

    def test_result_is_seed_result(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        result = seed_campaign_with_pack(campaign_dir, pack_path, dry_run=True)
        assert isinstance(result, SeedResult)

    def test_apply_persists_actor_tags(self, tmp_path: Path) -> None:
        pack_data = {
            **_PACK_DATA,
            "player_side": {
                "label": "The Party",
                "actors": [
                    {"slug": "mara", "display_name": "Mara", "actor_type": "pc",
                     "tags": ["trait:veteran", "level:level-1"]},
                ],
            },
        }
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path, pack_data)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        mara = repo.get_actor(derive_actor_id("test-campaign", "mara"))
        repo.close()
        assert mara is not None
        assert set(mara["tags"]) >= {"trait:veteran", "level:level-1"}

    def test_force_reseed_persists_actor_tags(self, tmp_path: Path) -> None:
        pack_data = {
            **_PACK_DATA,
            "player_side": {
                "label": "The Party",
                "actors": [
                    {"slug": "mara", "display_name": "Mara", "actor_type": "pc",
                     "tags": ["trait:veteran"]},
                ],
            },
        }
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path, pack_data)
        seed_campaign_with_pack(campaign_dir, pack_path)
        seed_campaign_with_pack(campaign_dir, pack_path, force=True)
        repo = _open_repo(campaign_dir)
        mara = repo.get_actor(derive_actor_id("test-campaign", "mara"))
        repo.close()
        assert mara is not None
        assert "trait:veteran" in mara["tags"]

    def test_force_reseed_preserves_playbook_and_room(self, tmp_path: Path) -> None:
        # The seed pack does not own playbook_slug or room_id (assigned by the
        # publish pipeline / movement). A --force reseed must not null them.
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)

        repo = _open_repo(campaign_dir)
        mara = next(a for a in repo.get_actors_by_campaign("campaign:test-campaign")
                    if a["slug"] == "mara")
        repo.save_actor(mara["actor_id"], "campaign:test-campaign", "pc", "mara", "Mara",
                        playbook_slug="fighter", room_id="r1")
        repo.close()

        seed_campaign_with_pack(campaign_dir, pack_path, force=True)

        repo = _open_repo(campaign_dir)
        mara = next(a for a in repo.get_actors_by_campaign("campaign:test-campaign")
                    if a["slug"] == "mara")
        repo.close()
        assert mara["playbook_slug"] == "fighter"
        assert mara["room_id"] == "r1"

    def test_seed_rejects_room_id_absent_from_dungeon_model(self, tmp_path: Path) -> None:
        # §4.3 live gate: when the campaign has a dungeon.json, a seed room-id that
        # matches no Room.id must fail loudly rather than silently never scope.
        campaign_dir = _make_campaign_dir(tmp_path)
        _write_dungeon(campaign_dir)
        pack_path = _write_pack(tmp_path, _pack_with_room_clock("NO-SUCH-ROOM"))
        with pytest.raises(ValueError, match="NO-SUCH-ROOM"):
            seed_campaign_with_pack(campaign_dir, pack_path)

    def test_seed_plants_room_records_from_dungeon_model(self, tmp_path: Path) -> None:
        # Slice B0: when the campaign carries a dungeon.json, every dungeon room
        # is projected into a first-class `rooms` record (summary from Room.note).
        campaign_dir = _make_campaign_dir(tmp_path)
        _write_dungeon(campaign_dir)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        rooms = {r["room_id"]: r for r in repo.get_rooms("campaign:test-campaign")}
        repo.close()
        assert "1-A" in rooms
        assert rooms["1-A"]["level_id"] == "level:1"
        assert rooms["1-A"]["summary"]  # non-empty, sourced from the room note

    def test_reseed_without_force_preserves_room_enrichment(self, tmp_path: Path) -> None:
        # A plain reseed must skip existing rooms, not clobber authored tags /
        # quest_role the populate scripts added (mirrors actors/clocks skip).
        campaign_dir = _make_campaign_dir(tmp_path)
        _write_dungeon(campaign_dir)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        # Simulate populate enrichment: author a lore tag on a room.
        from dungeon_daddy.rpg.models import RoomState
        repo = _open_repo(campaign_dir)
        row = repo.get_room("campaign:test-campaign", "1-A")
        repo.save_room(RoomState(**row).model_copy(update={"tags": ["theme:history"]}))
        repo.close()

        seed_campaign_with_pack(campaign_dir, pack_path)  # plain reseed

        repo = _open_repo(campaign_dir)
        room = repo.get_room("campaign:test-campaign", "1-A")
        repo.close()
        assert "theme:history" in room["tags"]  # enrichment survived

    def test_reseed_with_force_preserves_room_enrichment(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        _write_dungeon(campaign_dir)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        from dungeon_daddy.rpg.models import RoomState
        repo = _open_repo(campaign_dir)
        row = repo.get_room("campaign:test-campaign", "1-A")
        repo.save_room(RoomState(**row).model_copy(update={"tags": ["theme:history"]}))
        repo.close()

        seed_campaign_with_pack(campaign_dir, pack_path, force=True)  # force reseed

        repo = _open_repo(campaign_dir)
        room = repo.get_room("campaign:test-campaign", "1-A")
        repo.close()
        assert "theme:history" in room["tags"]  # force refreshes but preserves tags

    def test_seed_plants_no_rooms_without_dungeon_model(self, tmp_path: Path) -> None:
        # Back-compat: no dungeon.json → no room projection (the shipped seed_data
        # folders have no colocated dungeon model).
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path)
        seed_campaign_with_pack(campaign_dir, pack_path)
        repo = _open_repo(campaign_dir)
        rooms = repo.get_rooms("campaign:test-campaign")
        repo.close()
        assert rooms == []

    def test_seed_accepts_room_id_present_in_dungeon_model(self, tmp_path: Path) -> None:
        campaign_dir = _make_campaign_dir(tmp_path)
        _write_dungeon(campaign_dir)  # tomb rooms include "1-A"
        pack_path = _write_pack(tmp_path, _pack_with_room_clock("1-A"))
        seed_campaign_with_pack(campaign_dir, pack_path)  # no raise
        repo = _open_repo(campaign_dir)
        clocks = repo.get_clocks("campaign:test-campaign")
        repo.close()
        assert any(c["scope_room_id"] == "1-A" for c in clocks)

    def test_dry_run_stays_a_pure_preview_despite_room_mismatch(self, tmp_path: Path) -> None:
        # The §4.3 gate is on the write path only — a --dry-run preview must never
        # raise (or write), even against a live dungeon.json the seed mismatches.
        campaign_dir = _make_campaign_dir(tmp_path)
        _write_dungeon(campaign_dir)
        pack_path = _write_pack(tmp_path, _pack_with_room_clock("NO-SUCH-ROOM"))
        result = seed_campaign_with_pack(campaign_dir, pack_path, dry_run=True)
        assert isinstance(result, SeedResult)
        assert not (campaign_dir / "campaign.duckdb").exists()

    def test_seed_skips_room_validation_without_dungeon_model(self, tmp_path: Path) -> None:
        # Back-compat: no dungeon.json in the campaign folder → the gate is skipped
        # (the shipped seed_data folders have no colocated dungeon model).
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path, _pack_with_room_clock("NO-SUCH-ROOM"))
        seed_campaign_with_pack(campaign_dir, pack_path)  # no raise
        repo = _open_repo(campaign_dir)
        clocks = repo.get_clocks("campaign:test-campaign")
        repo.close()
        assert any(c["scope_room_id"] == "NO-SUCH-ROOM" for c in clocks)

    def test_force_reseed_persists_clock_metadata(self, tmp_path: Path) -> None:
        pack_data = {
            **_PACK_DATA,
            "clocks": [
                {
                    "slug": "bone-warden-stirs",
                    "label": "The Bone Warden Stirs",
                    "segments": 6,
                    "category": "danger",
                    "clock_level": "room",
                    "scope_room_id": "bone-vault",
                    "action_tags": ["fight", "move"],
                    "stakes": "The warden's bones rattle.",
                    "completion_effect": "The warden rises.",
                }
            ],
        }
        campaign_dir = _make_campaign_dir(tmp_path)
        pack_path = _write_pack(tmp_path, pack_data)
        seed_campaign_with_pack(campaign_dir, pack_path, force=True)
        repo = _open_repo(campaign_dir)
        clocks = repo.get_clocks("campaign:test-campaign")
        repo.close()
        clock = next(c for c in clocks if c["label"] == "The Bone Warden Stirs")
        assert clock["clock_level"] == "room"
        assert clock["scope_room_id"] == "bone-vault"
        assert clock["action_tags"] == ["fight", "move"]
        assert clock["category"] == "danger"
        assert clock["stakes"] == "The warden's bones rattle."

    def test_force_reseed_removes_stale_clocks(self, tmp_path: Path) -> None:
        # First seed with a clock that won't be in the second seed pack
        stale_pack = {
            **_PACK_DATA,
            "clocks": [
                {
                    "slug": "old-clock",
                    "label": "Old Stale Clock",
                    "segments": 4,
                    "category": "danger",
                }
            ],
        }
        new_pack = {
            **_PACK_DATA,
            "clocks": [
                {
                    "slug": "new-clock",
                    "label": "New Clock",
                    "segments": 6,
                    "category": "ritual",
                }
            ],
        }
        campaign_dir = _make_campaign_dir(tmp_path)
        stale_path = tmp_path / "stale.json"
        stale_path.write_text(json.dumps(stale_pack), encoding="utf-8")
        new_path = tmp_path / "new.json"
        new_path.write_text(json.dumps(new_pack), encoding="utf-8")

        seed_campaign_with_pack(campaign_dir, stale_path)
        seed_campaign_with_pack(campaign_dir, new_path, force=True)

        repo = _open_repo(campaign_dir)
        clocks = repo.get_clocks("campaign:test-campaign")
        repo.close()
        labels = {c["label"] for c in clocks}
        assert "New Clock" in labels
        assert "Old Stale Clock" not in labels
