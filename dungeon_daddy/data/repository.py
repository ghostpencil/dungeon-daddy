"""DungeonRepository — load/save dungeon JSON and room memory markdown."""
from __future__ import annotations

import importlib.resources
import json
import logging
import tempfile
from datetime import date
from pathlib import Path

from dungeon_daddy.data.models import ContextDocType, Dungeon, SessionState

_log = logging.getLogger(__name__)


class DungeonRepository:
    def __init__(self, dungeons_dir: Path | None) -> None:
        """
        dungeons_dir must already exist. DungeonRepository does NOT create it.
        Call AppConfig.ensure_dirs() before constructing the repository.
        Pass None only when calling load_sample().
        """
        self._dir = dungeons_dir

    # ------------------------------------------------------------------
    # Dungeon CRUD
    # ------------------------------------------------------------------

    def list_dungeons(self) -> list[str]:
        """Return names of all dungeon subdirectories that contain dungeon.json."""
        return sorted(
            p.name
            for p in self._dir.iterdir()
            if p.is_dir() and (p / "dungeon.json").exists()
        )

    def load(self, name: str) -> Dungeon:
        """Load and validate dungeon by name. Raises FileNotFoundError."""
        path = self._dir / name / "dungeon.json"
        if not path.exists():
            raise FileNotFoundError(f"Dungeon not found: {path}")
        return Dungeon.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self, dungeon: Dungeon, name: str) -> None:
        """Serialise and write dungeon to <dungeons_dir>/<name>/dungeon.json atomically."""
        dungeon_dir = self._dir / name
        dungeon_dir.mkdir(parents=True, exist_ok=True)
        path = dungeon_dir / "dungeon.json"
        data = json.dumps(
            dungeon.model_dump(mode="json", by_alias=True),
            indent=2,
            ensure_ascii=False,
        )
        _atomic_write(path, data)

    # ------------------------------------------------------------------
    # Session state
    # ------------------------------------------------------------------

    def load_session(self, name: str) -> SessionState | None:
        """Load session state if it exists, else return None. Returns None on corrupt data."""
        path = self._dir / name / "session.json"
        if not path.exists():
            return None
        try:
            return SessionState.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception:
            _log.warning("Session file corrupt or unreadable, ignoring: %s", path)
            return None

    def save_session(self, state: SessionState) -> None:
        """Write session state to <dungeons_dir>/<dungeon_id>/session.json."""
        dungeon_dir = self._dir / state.dungeon_id
        dungeon_dir.mkdir(parents=True, exist_ok=True)
        path = dungeon_dir / "session.json"
        data = json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=False)
        _atomic_write(path, data)

    # ------------------------------------------------------------------
    # Sample dungeon
    # ------------------------------------------------------------------

    def load_sample(self) -> Dungeon:
        """Load the bundled Tomb of the Forgotten King sample."""
        pkg_files = importlib.resources.files("dungeon_daddy.data")
        raw = (
            pkg_files / "samples" / "tomb_of_the_forgotten_king.json"
        ).read_text(encoding="utf-8")
        return Dungeon.model_validate(json.loads(raw))

    # ------------------------------------------------------------------
    # Room memory (markdown layer)
    # ------------------------------------------------------------------

    def _memory_path(self, name: str, level_id: int) -> Path:
        return self._dir / name / "memory" / f"level_{level_id}.md"

    def load_room_memory(self, name: str, level_id: int) -> str:
        """Load the markdown memory for a level. Returns '' if none exists."""
        path = self._memory_path(name, level_id)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def save_room_memory(self, name: str, level_id: int, content: str) -> None:
        """Overwrite the markdown memory for a level. Creates directory if needed."""
        path = self._memory_path(name, level_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, content)

    # ------------------------------------------------------------------
    # Context docs (markdown layer)
    # ------------------------------------------------------------------

    def _context_doc_path(self, dungeon_name: str, doc_type: ContextDocType, level_id: int | None) -> Path:
        if doc_type is ContextDocType.LEVEL_DESIGN:
            if level_id is None:
                raise ValueError("level_id required for LEVEL_DESIGN context doc")
            filename = f"level_{level_id}_design.md"
        else:
            filename = f"{doc_type.value}.md"
        return self._dir / dungeon_name / filename

    def load_context_doc(self, dungeon_name: str, doc_type: ContextDocType, level_id: int | None = None) -> str:
        """Load a context doc. Returns '' if the file doesn't exist."""
        path = self._context_doc_path(dungeon_name, doc_type, level_id)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def save_context_doc(self, dungeon_name: str, doc_type: ContextDocType, content: str, level_id: int | None = None) -> None:
        """Write a context doc, creating the dungeon subdirectory if needed."""
        path = self._context_doc_path(dungeon_name, doc_type, level_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, content)

    def migrate_legacy_layout(self) -> None:
        """Move legacy root-level files into per-dungeon subdirectories."""
        import shutil
        for json_file in list(self._dir.glob("*.json")):
            stem = json_file.stem
            if stem.endswith("_session"):
                dungeon_name = stem[: -len("_session")]
                dest_dir = self._dir / dungeon_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                json_file.rename(dest_dir / "session.json")
            else:
                dest_dir = self._dir / stem
                dest_dir.mkdir(parents=True, exist_ok=True)
                json_file.rename(dest_dir / "dungeon.json")
        for memory_dir in list(self._dir.glob("*_memory")):
            if memory_dir.is_dir():
                dungeon_name = memory_dir.name[: -len("_memory")]
                dest = self._dir / dungeon_name / "memory"
                if not dest.exists():
                    shutil.move(str(memory_dir), str(dest))
                else:
                    memory_dir.rmdir()

    def append_room_event(
        self,
        name: str,
        level_id: int,
        room_id: str,
        room_name: str,
        event: str,
    ) -> None:
        """Append a dated event line to a room's section in the level memory file."""
        path = self._memory_path(name, level_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = path.read_text(encoding="utf-8") if path.exists() else ""

        section_header = f"## Room {room_id} — {room_name}"
        event_line = f"- {date.today().isoformat()}: {event}\n"

        if section_header not in existing:
            # Add level heading on first write, then the new section
            if not existing:
                existing = f"# Level {level_id} Play Memory\n\n"
            existing = existing.rstrip("\n") + f"\n\n{section_header}\n"

        # Find where to insert: after the section header, before the next ##
        lines = existing.splitlines(keepends=True)
        insert_at = len(lines)  # default: end of file
        in_section = False
        for i, line in enumerate(lines):
            if line.rstrip() == section_header:
                in_section = True
                continue
            if in_section and line.startswith("## "):
                insert_at = i
                break

        lines.insert(insert_at, event_line)
        _atomic_write(path, "".join(lines))


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically using a temp file + rename."""
    dir_ = path.parent
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_, delete=False, suffix=".tmp"
    ) as f:
        f.write(content)
        tmp_path = Path(f.name)
    tmp_path.replace(path)
