from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

_REQUIRED_FIELDS = {"id", "type", "campaign_id", "updated_at"}


def write_memory(path: Path, front_matter: dict[str, object], body: str) -> None:
    fm_text = yaml.safe_dump(front_matter, default_flow_style=False, allow_unicode=True)
    # yaml.safe_dump always ends with \n
    content = f"---\n{fm_text}---\n\n{body}"
    path.write_text(content, encoding="utf-8")


def read_memory(path: Path) -> tuple[dict[str, object], str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("File does not start with front matter delimiter '---'")
    rest = content[4:]  # strip leading ---\n
    close_idx = rest.find("\n---\n")
    if close_idx == -1:
        raise ValueError("No closing front matter delimiter found")
    fm_text = rest[: close_idx + 1]  # include the trailing \n
    raw_body = rest[close_idx + 5 :]  # after \n---\n
    body = raw_body.lstrip("\n")
    front_matter: dict[str, object] = yaml.safe_load(fm_text) or {}
    return front_matter, body


def compute_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_front_matter(data: dict[str, object]) -> None:
    missing = _REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"Missing required front matter fields: {', '.join(sorted(missing))}")


def write_fallout_markdown(fallout: object, base_dir: Path) -> Path:
    from dungeon_daddy.rpg.models import FalloutRecord  # local import avoids circular dep
    assert isinstance(fallout, FalloutRecord)

    tags = [f"track:{fallout.track_key}", f"fallout:{fallout.status}"]
    if fallout.actor_id:
        tags.append(f"actor:{fallout.actor_id}")

    fm: dict[str, object] = {
        "id": fallout.fallout_id,
        "type": "fallout",
        "campaign_id": fallout.campaign_id,
        "track": fallout.track_key,
        "severity": fallout.severity,
        "status": fallout.status,
        "tags": tags,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    body = f"# {fallout.title}\n\n## Summary\n\n{fallout.summary}\n"
    path = base_dir / f"{fallout.fallout_id}.md"
    write_memory(path, fm, body)
    return path
