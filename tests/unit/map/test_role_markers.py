from dungeon_daddy.map.dungeon_layout.role_markers import resolve_role_marker


def test_entrance_resolves_to_IN():
    assert resolve_role_marker("entrance") == "IN"


def test_objective_resolves_to_OBJ():
    assert resolve_role_marker("objective") == "OBJ"


def test_boss_resolves_to_BOSS():
    assert resolve_role_marker("boss") == "BOSS"


def test_hazard_resolves_to_bang():
    assert resolve_role_marker("hazard") == "!"


def test_key_room_resolves_to_KEY():
    assert resolve_role_marker("key_room") == "KEY"


def test_descent_resolves_to_down_arrow():
    assert resolve_role_marker("descent") == "↓"


def test_stairs_resolves_to_down_arrow():
    assert resolve_role_marker("stairs") == "↓"


def test_elevator_resolves_to_down_arrow():
    assert resolve_role_marker("elevator") == "↓"


def test_transition_resolves_to_down_arrow():
    assert resolve_role_marker("transition") == "↓"


def test_treasure_resolves_to_dollar():
    assert resolve_role_marker("treasure") == "$"


def test_hub_resolves_to_HUB():
    assert resolve_role_marker("hub") == "HUB"


def test_unknown_is_quiet():
    assert resolve_role_marker("unknown") is None


def test_side_room_is_quiet():
    assert resolve_role_marker("side_room") is None


def test_corridor_is_quiet():
    assert resolve_role_marker("corridor") is None


def test_hall_is_quiet():
    assert resolve_role_marker("hall") is None
