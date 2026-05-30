"""Dungeon layout pipeline — public entry point."""
from __future__ import annotations

from dataclasses import dataclass, field

from dungeon_daddy.data.models import Level
from dungeon_daddy.map.dungeon_layout.camera_fit import compute_layout_bounds
from dungeon_daddy.map.dungeon_layout.debug_overlay import DebugOverlay
from dungeon_daddy.map.dungeon_layout.labels import place_labels
from dungeon_daddy.map.dungeon_layout.models import LabelBox, LayoutBounds, RoomRect, RoutedEdge
from dungeon_daddy.map.dungeon_layout.ports import generate_ports
from dungeon_daddy.map.dungeon_layout.route_orthogonal import route_connections
from dungeon_daddy.map.dungeon_layout.seed_layout import compute_critical_path, compute_seed_layout
from dungeon_daddy.map.dungeon_layout.semantics import RoomRole, classify_all_roles, classify_template


@dataclass
class LayoutResult:
    rooms: dict[str, RoomRect]
    edges: list[RoutedEdge]
    labels: list[LabelBox]
    bounds: LayoutBounds
    debug_overlay: DebugOverlay
    room_names: dict[str, str] = field(default_factory=dict)
    room_roles: dict[str, RoomRole] = field(default_factory=dict)
    edge_labels: dict[str, str] = field(default_factory=dict)
    critical_path: list[str] = field(default_factory=list)


def run_layout_pipeline(level: Level) -> LayoutResult:
    """Run semantics → seed → ports → route → labels → camera_fit for *level*."""
    if not level.rooms:
        bounds = LayoutBounds(min_x=0.0, min_y=0.0, max_x=1.0, max_y=1.0)
        return LayoutResult(
            rooms={}, edges=[], labels=[], bounds=bounds,
            debug_overlay=DebugOverlay(enabled=False, bounds=bounds),
        )

    roles = classify_all_roles(level)
    template = classify_template(level, roles)
    rooms = compute_seed_layout(level, roles, template)
    room_ids = set(rooms)
    intra_conns = [c for c in level.connections if c.from_room in room_ids and c.to_room in room_ids]
    ports = generate_ports(rooms, intra_conns)
    edges = route_connections(rooms, ports, intra_conns)
    label_map = {f"{c.from_room}→{c.to_room}": c.type for c in intra_conns}
    labels = place_labels(edges, rooms, label_map)

    room_list = list(rooms.values())
    bounds = compute_layout_bounds(room_list, edges, labels, margin=40.0)

    room_names = {r.id: r.name for r in level.rooms}
    critical_path = compute_critical_path(level, roles)

    return LayoutResult(
        rooms=rooms,
        edges=edges,
        labels=labels,
        bounds=bounds,
        room_names=room_names,
        room_roles=roles,
        edge_labels=label_map,
        critical_path=critical_path,
        debug_overlay=DebugOverlay(
            enabled=False,
            rooms=room_list,
            obstacles=[r.inflate(16.0) for r in room_list],
            ports=list(ports.values()),
            edges=edges,
            labels=labels,
            bounds=bounds,
        ),
    )
