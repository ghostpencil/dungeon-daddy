"""Critical path presentation flags and config toggle for Graph Mode.

Determines which rooms and connections are on the critical path and
whether they should be visually distinguished.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CriticalPathPresentationResult:
    critical_path_room_ids: set[str]
    critical_path_connection_ids: set[str]
    is_visually_distinguished: bool
    warnings: list[str] = field(default_factory=list)


class CriticalPathPresenter:
    def present(
        self,
        critical_path: list[str] | None,
        emphasize_critical_path: bool,
    ) -> CriticalPathPresentationResult:
        if not emphasize_critical_path:
            return CriticalPathPresentationResult(
                critical_path_room_ids=set(),
                critical_path_connection_ids=set(),
                is_visually_distinguished=False,
            )

        if not critical_path:
            return CriticalPathPresentationResult(
                critical_path_room_ids=set(),
                critical_path_connection_ids=set(),
                is_visually_distinguished=False,
                warnings=["CRITICAL_PATH_NOT_DISTINGUISHED"],
            )

        connection_ids = {
            f"{critical_path[i]}→{critical_path[i + 1]}"
            for i in range(len(critical_path) - 1)
        }
        return CriticalPathPresentationResult(
            critical_path_room_ids=set(critical_path),
            critical_path_connection_ids=connection_ids,
            is_visually_distinguished=True,
        )
