"""Memory coordination (Phase 51.7, Slice 6).

:class:`MemoryCoordinator` owns the memory seam extracted from ``PlayView``:

* the ``/remember`` command (:meth:`handle_remember`) and the silent
  ``[REMEMBER: …]`` DM hook (:meth:`auto_remember`) — both append a dated room
  event to the party level's play-memory markdown;
* :meth:`extract_remember` — split a ``[REMEMBER: …]`` marker out of DM text;
* :meth:`load_memory_entries` — populate the MEM panel from the memory store;
* :meth:`persist_pending_commit` — write a MEM-tab approve/reject to disk;
* the level-memory overlay's load/save persistence
  (:meth:`has_level_memory` / :meth:`load_level_memory` / :meth:`save_level_memory`).

The overlay *widgets* (input box, backdrop, buttons) stay in the view — this
coordinator owns only the persistence behind them.

Pure play-layer object — imports no ``arcade`` (see the package docstring for
the dependency direction). It receives the view's UI/repo/side-effect seams as
narrow callables (ports); it never holds a ``PlayView`` reference.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from dungeon_daddy.memory.models import MemoryEntry

if TYPE_CHECKING:
    from dungeon_daddy.play.session_context import PlaySessionContext


class MemoryCoordinator:
    """Records play memory and reflects it in the MEM panel + overlay."""

    _REMEMBER_RE = re.compile(r"\[REMEMBER:\s*(.+?)\]", re.IGNORECASE)

    def __init__(
        self,
        session: PlaySessionContext,
        *,
        post_message: Callable[[str, str], None],
        append_room_event: Callable[[str, int, str, str, str], None],
        load_room_memory: Callable[[str, int], str],
        save_room_memory: Callable[[str, int, str], None],
        set_entries: Callable[[list[MemoryEntry]], None],
        pop_pending_commit: Callable[[], MemoryEntry | None],
        refresh_memory_state: Callable[[], None],
    ) -> None:
        self._session = session
        self._post_message = post_message
        self._append_room_event = append_room_event
        self._load_room_memory = load_room_memory
        self._save_room_memory = save_room_memory
        self._set_entries = set_entries
        self._pop_pending_commit = pop_pending_commit
        self._refresh_memory_state = refresh_memory_state

    # -- /remember + auto-remember ------------------------------------------

    def extract_remember(self, text: str) -> tuple[str | None, str]:
        """Split a ``[REMEMBER: …]`` marker out of DM text.

        Returns ``(remembered_or_None, cleaned_text)`` — the captured note (or
        ``None`` when no marker is present) and the text with the first marker
        removed.
        """
        match = self._REMEMBER_RE.search(text)
        if match is None:
            return None, text
        remembered = match.group(1).strip()
        cleaned = self._REMEMBER_RE.sub("", text, count=1).strip()
        return remembered, cleaned

    def handle_remember(self, event: str) -> None:
        """``/remember`` command: append a dated room event, confirm in chat."""
        session = self._session
        if session.dungeon is None or session.state is None:
            self._post_message("system", "No dungeon loaded.")
            return
        if not session.state.current_room_id:
            self._post_message(
                "system", "No room selected — click a room first."
            )
            return
        if not self._record_room_event(event):
            return
        self._post_message("system", f"Remembered: {event}")
        self._refresh_memory_state()

    def auto_remember(self, event: str) -> None:
        """Silent ``[REMEMBER: …]`` hook: append a dated room event, note it."""
        session = self._session
        if session.dungeon is None or session.state is None:
            return
        if not session.state.current_room_id:
            return
        if not self._record_room_event(event):
            return
        self._post_message("system", f"📝 Noted: {event}")

    def _record_room_event(self, event: str) -> bool:
        """Append ``event`` under the party room's section of the level memory.

        Returns ``False`` (no write) when the party's level can't be resolved.
        """
        session = self._session
        level = session.current_level()
        if level is None or session.state is None:
            return False
        room_id = session.state.current_room_id
        if not room_id:
            return False
        room = session.current_room()
        room_name = room.name if room is not None else room_id
        self._append_room_event(
            session.state.dungeon_id, level.id, room_id, room_name, event,
        )
        return True

    # -- MEM-tab entries + commit persistence -------------------------------

    def load_memory_entries(self) -> None:
        """Populate the MEM panel with the campaign's memory entries + tags."""
        session = self._session
        repo = session.mem_repo
        if repo is None:
            return
        campaign_id = session.campaign_id or (
            session.state.dungeon_id if session.state else None
        )
        if campaign_id is None:
            return
        entries = [
            MemoryEntry(
                memory_id=r["memory_id"],
                campaign_id=r["campaign_id"],
                type=r["type"],
                title=r["title"],
                summary=r["summary"],
                status=r["status"],
                importance=r["importance"],
                markdown_path=r["markdown_path"],
                checksum=r["checksum"],
                tags=repo.get_memory_tags(r["memory_id"]),
            )
            for r in repo.get_memory_entries_by_campaign(campaign_id)
        ]
        self._set_entries(entries)

    def persist_pending_commit(self) -> None:
        """Write a pending MEM-tab approve/reject to the memory store."""
        commit = self._pop_pending_commit()
        repo = self._session.mem_repo
        if commit is None or repo is None:
            return
        repo.update_memory_status(commit.memory_id, commit.status)

    # -- level-memory overlay persistence -----------------------------------

    def has_level_memory(self) -> bool:
        """Whether the party's current level has any saved play memory."""
        session = self._session
        level = session.current_level()
        if level is None or session.state is None:
            return False
        return bool(self._load_room_memory(session.state.dungeon_id, level.id))

    def load_level_memory(self) -> tuple[int, str] | None:
        """``(level_id, content)`` for the overlay, or ``None`` if unloadable."""
        session = self._session
        level = session.current_level()
        if level is None or session.state is None:
            return None
        content = self._load_room_memory(session.state.dungeon_id, level.id)
        return level.id, content

    def save_level_memory(self, level_id: int, content: str) -> None:
        """Persist the overlay's edited ``content`` for ``level_id``."""
        session = self._session
        if session.state is None:
            return
        self._save_room_memory(session.state.dungeon_id, level_id, content)
