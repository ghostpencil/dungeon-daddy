import pytest
from pydantic import ValidationError

from dungeon_daddy.rpg.models import FactionState


class TestFactionState:
    def test_validates_with_defaults(self) -> None:
        f = FactionState(
            faction_id="f1",
            campaign_id="c1",
            slug="ossuary-cult",
            display_name="The Ossuary Cult",
        )
        assert f.reputation == "neutral"
        assert f.tier == 0
        assert f.status == "active"
        assert f.tags == []

    def test_rejects_invalid_reputation(self) -> None:
        with pytest.raises(ValidationError):
            FactionState(
                faction_id="f1",
                campaign_id="c1",
                slug="test",
                display_name="Test",
                reputation="enemy",
            )
