from dungeon_daddy.rpg.dice import roll_pool


def test_partial_outcome_from_fixed_dice() -> None:
    result = roll_pool(pool=2, fixed=[5, 2])
    assert result.highest == 5
    assert result.outcome == "partial"


def test_miss_outcome() -> None:
    result = roll_pool(pool=2, fixed=[3, 1])
    assert result.outcome == "miss"


def test_full_outcome_single_six() -> None:
    result = roll_pool(pool=2, fixed=[6, 3])
    assert result.outcome == "full"


def test_critical_outcome_double_six() -> None:
    result = roll_pool(pool=3, fixed=[6, 6, 2])
    assert result.outcome == "critical"


def test_zero_pool_uses_one_die() -> None:
    result = roll_pool(pool=0, fixed=[4])
    assert result.outcome == "partial"
