"""Endpoint emphasis detection and spacing check for Graph Mode.

Identifies the visual endpoint of a dungeon (boss, objective, exit-family)
and checks whether it has sufficient spacing from its neighbors.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from dungeon_daddy.data.models import Connection
from dungeon_daddy.map.dungeon_layout.models import RoomRect
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.semantics import RoomRole

_MIN_ENDPOINT_SPACING: float = 20.0

_ENDPOINT_PRIORITY: list[str] = ["boss", "objective", "exit", "descent", "elevator", "stairs"]
_ENDPOINT_ROLES: frozenset[str] = frozenset(_ENDPOINT_PRIORITY)


@dataclass
class EndpointEmphasisResult:
    endpoint_room_id: str | None
    endpoint_role: str | None
    is_emphasized: bool
    has_sufficient_spacing: bool
    warnings: list[str] = field(default_factory=list)


def _rect_gap(a: RoomRect, b: RoomRect) -> float:
    dx = max(0.0, max(a.left - b.right, b.left - a.right))
    dy = max(0.0, max(a.bottom - b.top, b.bottom - a.top))
    if dx == 0.0 and dy == 0.0:
        return 0.0
    if dx == 0.0:
        return dy
    if dy == 0.0:
        return dx
    return math.sqrt(dx * dx + dy * dy)


class EndpointEmphasisDetector:
    _resolver = GraphRoomStyleResolver()

    def detect(
        self,
        roles: dict[str, RoomRole],
        rooms: dict[str, RoomRect],
        connections: list[Connection],
        critical_path: list[str] | None = None,
    ) -> EndpointEmphasisResult:
        endpoint_id = self._find_endpoint(roles, critical_path)

        warnings: list[str] = []
        if endpoint_id is None:
            return EndpointEmphasisResult(
                endpoint_room_id=None,
                endpoint_role=None,
                is_emphasized=False,
                has_sufficient_spacing=True,
                warnings=["AMBIGUOUS_ENDPOINT_ROLE"],
            )

        role = roles.get(endpoint_id, "unknown")
        style = self._resolver.resolve(role)
        is_emphasized = style.priority in ("high", "medium")

        has_sufficient_spacing, spacing_warnings = self._check_spacing(
            endpoint_id, rooms, connections
        )
        warnings.extend(spacing_warnings)

        return EndpointEmphasisResult(
            endpoint_room_id=endpoint_id,
            endpoint_role=role,
            is_emphasized=is_emphasized,
            has_sufficient_spacing=has_sufficient_spacing,
            warnings=warnings,
        )

    def _find_endpoint(
        self,
        roles: dict[str, RoomRole],
        critical_path: list[str] | None,
    ) -> str | None:
        for role_key in _ENDPOINT_PRIORITY:
            for room_id, role in roles.items():
                if role == role_key:
                    return room_id
        if critical_path:
            last = critical_path[-1]
            if last in roles:
                return last
        return None

    def _check_spacing(
        self,
        endpoint_id: str,
        rooms: dict[str, RoomRect],
        connections: list[Connection],
    ) -> tuple[bool, list[str]]:
        endpoint_rect = rooms.get(endpoint_id)
        if endpoint_rect is None:
            return True, []

        neighbor_ids: set[str] = set()
        for conn in connections:
            if conn.from_room == endpoint_id:
                neighbor_ids.add(conn.to_room)
            elif conn.to_room == endpoint_id:
                neighbor_ids.add(conn.from_room)

        for nid in neighbor_ids:
            neighbor_rect = rooms.get(nid)
            if neighbor_rect is None:
                continue
            gap = _rect_gap(endpoint_rect, neighbor_rect)
            if gap < _MIN_ENDPOINT_SPACING:
                return False, ["ENDPOINT_NOT_EMPHASIZED"]

        return True, []
