from dungeon_daddy.rpg.actor_control import filter_player_actors, is_player_controlled
from dungeon_daddy.rpg.models import ActorState


def _actor(actor_type: str, status: str = "active") -> ActorState:
    return ActorState(
        actor_id=f"{actor_type}-1",
        campaign_id="camp-1",
        actor_type=actor_type,  # type: ignore[arg-type]
        slug=actor_type,
        display_name=actor_type.upper(),
        status=status,  # type: ignore[arg-type]
    )


class TestIsPlayerControlled:
    def test_pc_is_player_controlled(self):
        assert is_player_controlled("pc") is True

    def test_npc_is_not_player_controlled(self):
        assert is_player_controlled("npc") is False

    def test_monster_is_not_player_controlled(self):
        assert is_player_controlled("monster") is False

    def test_dungeon_is_not_player_controlled(self):
        assert is_player_controlled("dungeon") is False

    def test_faction_is_not_player_controlled(self):
        assert is_player_controlled("faction") is False

    def test_dungeon_presence_is_not_player_controlled(self):
        assert is_player_controlled("dungeon_presence") is False


class TestFilterPlayerActors:
    def test_returns_active_pc_actors(self):
        actors = [_actor("pc"), _actor("npc"), _actor("monster")]
        result = filter_player_actors(actors)
        assert len(result) == 1
        assert result[0].actor_type == "pc"

    def test_excludes_inactive_pc(self):
        actors = [_actor("pc", "active"), _actor("pc", "inactive")]
        result = filter_player_actors(actors)
        assert len(result) == 1

    def test_excludes_dead_pc(self):
        actors = [_actor("pc", "active"), _actor("pc", "dead")]
        result = filter_player_actors(actors)
        assert len(result) == 1

    def test_empty_list_returns_empty(self):
        assert filter_player_actors([]) == []

    def test_no_pcs_returns_empty(self):
        actors = [_actor("npc"), _actor("dungeon")]
        assert filter_player_actors(actors) == []
