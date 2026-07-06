from __future__ import annotations

from pathlib import Path

from dungeon_daddy.campaign.manifest import CampaignManifest


class CampaignSeedLibrary:
    def __init__(self, seeds_dir: Path) -> None:
        self._dir = seeds_dir

    def save(self, manifest: CampaignManifest) -> None:
        dest = self._dir / manifest.slug
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "campaign.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )

    def load(self, slug: str) -> CampaignManifest:
        path = self._dir / slug / "campaign.json"
        if not path.exists():
            raise FileNotFoundError(f"Campaign seed not found: {slug!r}")
        return CampaignManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def exists(self, slug: str) -> bool:
        return (self._dir / slug / "campaign.json").exists()

    def list(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(
            p.name for p in self._dir.iterdir()
            if p.is_dir() and (p / "campaign.json").exists()
        )
