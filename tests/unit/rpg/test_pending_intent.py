import pytest
from pydantic import ValidationError

from dungeon_daddy.rpg.intent import PendingIntent


def test_pending_intent_construction_with_all_fields():
    pi = PendingIntent(
        actor_id="actor-1",
        raw_text="I study the mural",
        suggested_action_keys=["study", "sense", "focus"],
        suggested_primary_action="study",
        stakes_text="the mural may study her back",
        status="awaiting_confirmation",
    )
    assert pi.suggested_action_keys == ["study", "sense", "focus"]
    assert pi.suggested_primary_action == "study"
    assert pi.stakes_text == "the mural may study her back"


def test_pending_intent_construction_with_defaults():
    pi = PendingIntent(actor_id="actor-1", raw_text="I study the mural")
    assert pi.actor_id == "actor-1"
    assert pi.raw_text == "I study the mural"
    assert pi.suggested_action_keys == []
    assert pi.suggested_primary_action is None
    assert pi.stakes_text == ""
    assert pi.status == "awaiting_confirmation"


def test_pending_intent_invalid_status_raises():
    with pytest.raises(ValidationError):
        PendingIntent(actor_id="actor-1", raw_text="text", status="rolling")  # type: ignore[arg-type]


def test_pending_intent_status_resolved():
    pi = PendingIntent(actor_id="actor-1", raw_text="text", status="resolved")
    assert pi.status == "resolved"


def test_pending_intent_status_cancelled():
    pi = PendingIntent(actor_id="actor-1", raw_text="text", status="cancelled")
    assert pi.status == "cancelled"
