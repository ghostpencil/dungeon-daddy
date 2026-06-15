from pathlib import Path

import pytest

from dungeon_daddy.campaign.manifest import CampaignManifest
from dungeon_daddy.campaign.seed_library import CampaignSeedLibrary


def _manifest(slug: str = "bone-cathedral") -> CampaignManifest:
    return CampaignManifest(slug=slug, title="Bone Cathedral", dungeon_slug="bone-cathedral")


def test_exists_true_for_saved_false_for_missing(tmp_path: Path) -> None:
    lib = CampaignSeedLibrary(tmp_path)
    lib.save(_manifest("bone-cathedral"))

    assert lib.exists("bone-cathedral") is True
    assert lib.exists("no-such-slug") is False


def test_list_returns_sorted_slugs(tmp_path: Path) -> None:
    lib = CampaignSeedLibrary(tmp_path)
    lib.save(_manifest("zebra-run"))
    lib.save(_manifest("abyss-gate"))
    lib.save(_manifest("midnight-crypt"))

    assert lib.list() == ["abyss-gate", "midnight-crypt", "zebra-run"]


def test_load_missing_slug_raises(tmp_path: Path) -> None:
    lib = CampaignSeedLibrary(tmp_path)

    with pytest.raises(FileNotFoundError):
        lib.load("no-such-slug")


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    lib = CampaignSeedLibrary(tmp_path)
    m = _manifest()

    lib.save(m)
    loaded = lib.load(m.slug)

    assert loaded == m
