"""Camera auto-fit: compute LayoutBounds covering all layout geometry."""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.models import LabelBox, LayoutBounds, RoomRect, RoutedEdge


def compute_layout_bounds(
    rooms: list[RoomRect],
    edges: list[RoutedEdge],
    labels: list[LabelBox],
    margin: float = 0.0,
) -> LayoutBounds:
    """Return tight LayoutBounds covering all geometry, expanded by margin."""
    if not rooms and not edges and not labels:
        raise ValueError("Cannot compute bounds of empty layout")

    xs: list[float] = []
    ys: list[float] = []

    for r in rooms:
        xs += [r.left, r.right]
        ys += [r.bottom, r.top]

    for e in edges:
        for px, py in e.points:
            xs.append(px)
            ys.append(py)

    for lb in labels:
        xs += [lb.x, lb.right]
        ys += [lb.y, lb.top]

    bounds = LayoutBounds(
        min_x=min(xs),
        min_y=min(ys),
        max_x=max(xs),
        max_y=max(ys),
    )
    return bounds.expand(margin)
