"""Integration tests: seeded campaign clocks filter correctly under world reaction."""
from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActionRequest, ActionResolution, ActorState, ClockState, StressTrack
from dungeon_daddy.rpg.seed_pack import SeedPack, apply_seed_pack, derive_actor_id, derive_clock_id
from dungeon_daddy.rpg.service import RpgService
from dungeon_daddy.rpg.world_reaction import compute_world_reaction

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(db_path=tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _make_miss_resolution(campaign_id: str, actor_id: str, action_key: str) -> ActionResolution:
    return ActionResolution(
        resolution_id="res-test",
        campaign_id=campaign_id,
        actor_id=actor_id,
        action_key=action_key,
        outcome="miss",
        dice_rolled=[1, 2],
        highest=2,
        position="risky",
        effect="standard",
    )


def _minimal_seed(campaign_slug: str) -> dict:
    return {
        "campaign_slug": campaign_slug,
        "player_side": {
            "label": "The Party",
            "actors": [
                {"slug": "hero", "display_name": "Hero", "actor_type": "pc",
                 "actions": {"fight": 2, "move": 1}, "stress_tracks": ["body"]},
            ],
        },
        "dungeon_side": {"actors": []},
        "memories": [],
        "room_threats": [],
    }


class TestScopedClockFiltering:
    def test_room_clock_advances_only_in_matching_room(self, repo: MemoryRepository) -> None:
        """Room clock with scope_room_id only advances when action is in that room."""
        campaign_id = "camp-test"
        actor_id = derive_actor_id("test-campaign", "hero")

        seed_data = {
            **_minimal_seed("test-campaign"),
            "clocks": [
                {
                    "slug": "room-trap",
                    "label": "Room Trap Active",
                    "segments": 4,
                    "category": "danger",
                    "clock_level": "room",
                    "scope_room_id": "boiler-room",
                    "action_tags": ["fight", "move"],
                    "stakes": "The trap primes.",
                    "completion_effect": "Trap triggers.",
                },
                {
                    "slug": "dungeon-wide",
                    "label": "Dungeon Alert",
                    "segments": 6,
                    "category": "danger",
                    "clock_level": "dungeon",
                    "stakes": "Alert spreads.",
                    "completion_effect": "Full lockdown.",
                },
            ],
        }
        pack = SeedPack.model_validate(seed_data)
        apply_seed_pack(pack, campaign_id, repo, MIGRATIONS_DIR)

        clocks_before = {c["clock_id"]: c for c in repo.get_clocks(campaign_id)}
        room_clock_id = derive_clock_id("test-campaign", "room-trap")
        dungeon_clock_id = derive_clock_id("test-campaign", "dungeon-wide")

        threat_clocks = [
            ClockState(**{k: v for k, v in c.items()})
            for c in clocks_before.values()
        ]
        pc_actor = ActorState(
            actor_id=actor_id, campaign_id=campaign_id, actor_type="pc",
            slug="hero", display_name="Hero",
        )
        body_track = StressTrack(track_key="body", capacity=6, filled=0)

        resolution = _make_miss_resolution(campaign_id, actor_id, "fight")

        # Action in boiler-room: room clock should advance, dungeon clock should too
        reaction_in_room = compute_world_reaction(
            resolution, threat_clocks, [(pc_actor, {"body": body_track})],
            current_room_id="boiler-room",
        )
        advanced_in_room = {line.clock_id for line in reaction_in_room.clock_lines}
        assert room_clock_id in advanced_in_room
        assert dungeon_clock_id in advanced_in_room

        # Action in different room: room clock should NOT advance, dungeon clock should
        reaction_elsewhere = compute_world_reaction(
            resolution, threat_clocks, [(pc_actor, {"body": body_track})],
            current_room_id="library",
        )
        advanced_elsewhere = {line.clock_id for line in reaction_elsewhere.clock_lines}
        assert room_clock_id not in advanced_elsewhere
        assert dungeon_clock_id in advanced_elsewhere

    def test_room_clock_metadata_survives_after_apply(self, repo: MemoryRepository) -> None:
        """After apply_seed_pack, room clock scope metadata is readable from get_clocks."""
        campaign_id = "camp-test"
        seed_data = {
            **_minimal_seed("test-campaign"),
            "clocks": [
                {
                    "slug": "entry-trap",
                    "label": "Entry Trap Primed",
                    "segments": 4,
                    "category": "danger",
                    "clock_level": "room",
                    "scope_room_id": "entry-chamber",
                    "action_tags": ["fight", "move"],
                    "stakes": "The trap is ready.",
                    "completion_effect": "Trap fires.",
                },
            ],
        }
        pack = SeedPack.model_validate(seed_data)
        apply_seed_pack(pack, campaign_id, repo, MIGRATIONS_DIR)

        clocks = {c["clock_id"]: c for c in repo.get_clocks(campaign_id)}
        clock_id = derive_clock_id("test-campaign", "entry-trap")
        clock = clocks[clock_id]

        assert clock["clock_level"] == "room"
        assert clock["scope_room_id"] == "entry-chamber"
        assert clock["action_tags"] == ["fight", "move"]
        assert clock["stakes"] == "The trap is ready."
        assert clock["completion_effect"] == "Trap fires."

    def test_level_clock_advances_regardless_of_room(self, repo: MemoryRepository) -> None:
        """Level clock with no scope_room_id advances from any room on the campaign."""
        campaign_id = "camp-test"
        actor_id = derive_actor_id("test-campaign", "hero")

        seed_data = {
            **_minimal_seed("test-campaign"),
            "clocks": [
                {
                    "slug": "level-alert",
                    "label": "Level Alert",
                    "segments": 6,
                    "category": "danger",
                    "clock_level": "level",
                    "level_id": "level-2",
                    "action_tags": ["fight", "move"],
                    "stakes": "Level-wide alert rises.",
                    "completion_effect": "Full patrol mobilization.",
                },
            ],
        }
        pack = SeedPack.model_validate(seed_data)
        apply_seed_pack(pack, campaign_id, repo, MIGRATIONS_DIR)

        clocks_data = repo.get_clocks(campaign_id)
        threat_clocks = [ClockState(**{k: v for k, v in c.items()}) for c in clocks_data]
        pc_actor = ActorState(
            actor_id=actor_id, campaign_id=campaign_id, actor_type="pc",
            slug="hero", display_name="Hero",
        )
        body_track = StressTrack(track_key="body", capacity=6, filled=0)
        resolution = _make_miss_resolution(campaign_id, actor_id, "fight")

        for room in ("level-2-room-a", "level-2-room-b", "completely-different-room"):
            reaction = compute_world_reaction(
                resolution, threat_clocks, [(pc_actor, {"body": body_track})],
                current_room_id=room,
            )
            level_clock_id = derive_clock_id("test-campaign", "level-alert")
            advanced = {line.clock_id for line in reaction.clock_lines}
            assert level_clock_id in advanced, f"Level clock should advance in room {room!r}"
