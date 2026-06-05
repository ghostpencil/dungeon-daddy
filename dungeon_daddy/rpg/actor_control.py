from dungeon_daddy.rpg.models import ActorState

_PLAYER_TYPES = {"pc"}
_ACTIVE_STATUSES = {"active"}


def is_player_controlled(actor_type: str) -> bool:
    return actor_type in _PLAYER_TYPES


def filter_player_actors(actors: list[ActorState]) -> list[ActorState]:
    return [a for a in actors if is_player_controlled(a.actor_type) and a.status in _ACTIVE_STATUSES]
