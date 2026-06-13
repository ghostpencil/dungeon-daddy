from __future__ import annotations

from dungeon_daddy.memory.context_bundle import ContextBundleBuilder
from dungeon_daddy.memory.models import ContextBundle
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import FactionState


class TestContextBundleFactionReputationsField:
    def test_context_bundle_has_faction_reputations_field(self) -> None:
        bundle = ContextBundle(
            bundle_id="b1",
            campaign_id="camp_001",
            mode="run_scene",
        )
        assert bundle.faction_reputations == []


class TestContextBundleFactionReputations:
    def test_build_returns_empty_faction_reputations_when_none_saved(
        self, repo: MemoryRepository
    ) -> None:
        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)
        assert bundle.faction_reputations == []

    def test_active_faction_appears_in_faction_reputations(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_faction(FactionState(
            faction_id="f001",
            campaign_id="camp_001",
            slug="ossuary-cult",
            display_name="The Ossuary Cult",
            concept="Remnants of the cult.",
            goal="Complete the rite.",
            status="active",
            reputation="cold",
            tier=1,
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)

        assert len(bundle.faction_reputations) == 1
        entry = bundle.faction_reputations[0]
        assert entry["slug"] == "ossuary-cult"
        assert entry["display_name"] == "The Ossuary Cult"
        assert entry["reputation"] == "cold"
        assert entry["goal"] == "Complete the rite."
        assert entry["tier"] == 1
        assert entry["status"] == "active"

    def test_inactive_and_dissolved_factions_excluded(
        self, repo: MemoryRepository
    ) -> None:
        repo.save_faction(FactionState(
            faction_id="f_active",
            campaign_id="camp_001",
            slug="guild-active",
            display_name="Active Guild",
            status="active",
            reputation="neutral",
            tier=0,
        ))
        repo.save_faction(FactionState(
            faction_id="f_inactive",
            campaign_id="camp_001",
            slug="guild-inactive",
            display_name="Inactive Guild",
            status="inactive",
            reputation="warm",
            tier=1,
        ))
        repo.save_faction(FactionState(
            faction_id="f_dissolved",
            campaign_id="camp_001",
            slug="guild-dissolved",
            display_name="Dissolved Guild",
            status="dissolved",
            reputation="allied",
            tier=2,
        ))

        bundle = ContextBundleBuilder(
            campaign_id="camp_001",
            scene_id=None,
            mode="run_scene",
            focus_actor_ids=[],
            token_budget=500,
        ).build(repo)

        slugs = {f["slug"] for f in bundle.faction_reputations}
        assert "guild-active" in slugs
        assert "guild-inactive" not in slugs
        assert "guild-dissolved" not in slugs
