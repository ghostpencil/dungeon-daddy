from dungeon_daddy.rpg.classifier import classify_intent


def test_fight_keyword_returns_fight():
    assert classify_intent("I attack the guard") == ["fight"]


def test_unknown_text_returns_empty():
    assert classify_intent("I wander around aimlessly") == []


def test_empty_string_returns_empty():
    assert classify_intent("") == []


def test_case_insensitive_matching():
    assert classify_intent("I ATTACK the Guard") == ["fight"]


def test_multiple_matches_ranked_by_count():
    # "sneak" and "dodge" → move=2; "open" → tinker=1 → move ranked first
    result = classify_intent("I sneak past and dodge the trap then open the door")
    assert result[0] == "move"
    assert "tinker" in result
    assert result.index("move") < result.index("tinker")


def test_single_match_each_returns_both():
    result = classify_intent("I attack and search the room")
    assert "fight" in result
    assert "sense" in result


def test_runes_does_not_trigger_move():
    # "run" is a substring of "runes" — must not false-positive as move
    result = classify_intent("I study the runes on the floor")
    assert "move" not in result


def test_study_verb_triggers_study_action():
    result = classify_intent("I study the ancient tablet")
    assert result and result[0] == "study"


def test_studies_conjugation_triggers_study_action():
    result = classify_intent("Talvas studies the runes on the floor")
    assert result and result[0] == "study"


def test_examine_triggers_study_action():
    result = classify_intent("I examine the inscription on the wall")
    assert result and result[0] == "study"
