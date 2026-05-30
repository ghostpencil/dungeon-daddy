"""Collision-aware label placement for the dungeon layout pipeline.

Places one LabelBox per routed connection, chosen from candidates at 25%,
50%, and 75% along the longest segment, scored by overlap with rooms and
other labels.  No Arcade dependency — pure Python.
"""
from __future__ import annotations

import math

from dungeon_daddy.map.dungeon_layout.models import LabelBox, RoomRect, RoutedEdge

_PADDING = 8.0
_FRACTIONS = (0.25, 0.50, 0.75)


def place_labels(
    edges: list[RoutedEdge],
    rooms: dict[str, RoomRect],
    labels: dict[str, str],
    label_w: float = 60.0,
    label_h: float = 14.0,
) -> list[LabelBox]:
    """Return one LabelBox per edge, collision-aware."""
    placed: list[LabelBox] = []
    for edge in edges:
        text = labels.get(edge.connection_id, "")
        box = _place_one(edge, text, rooms, placed, label_w, label_h)
        placed.append(box)
    return placed


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _place_one(
    edge: RoutedEdge,
    text: str,
    rooms: dict[str, RoomRect],
    placed: list[LabelBox],
    label_w: float,
    label_h: float,
) -> LabelBox:
    segment = _longest_segment(edge.points)
    candidates = _candidates(segment, label_w, label_h)
    best = min(candidates, key=lambda b: _score(b, rooms, placed, label_w, label_h))
    return LabelBox(
        connection_id=edge.connection_id,
        text=text,
        x=best[0],
        y=best[1],
        w=label_w,
        h=label_h,
    )


def _longest_segment(
    points: list[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float]]:
    best_len = -1.0
    best = (points[0], points[1]) if len(points) >= 2 else (points[0], points[0])
    for i in range(len(points) - 1):
        d = math.dist(points[i], points[i + 1])
        if d > best_len:
            best_len = d
            best = (points[i], points[i + 1])
    return best


def _candidates(
    segment: tuple[tuple[float, float], tuple[float, float]],
    label_w: float,
    label_h: float,
) -> list[tuple[float, float]]:
    (x1, y1), (x2, y2) = segment
    is_horizontal = abs(y2 - y1) <= abs(x2 - x1)
    result: list[tuple[float, float]] = []
    for frac in _FRACTIONS:
        mx = x1 + frac * (x2 - x1)
        my = y1 + frac * (y2 - y1)
        half_w, half_h = label_w / 2, label_h / 2
        if is_horizontal:
            result.append((mx - half_w, my + _PADDING))
            result.append((mx - half_w, my - label_h - _PADDING))
        else:
            result.append((mx + _PADDING, my - half_h))
            result.append((mx - label_w - _PADDING, my - half_h))
    return result


def _score(
    pos: tuple[float, float],
    rooms: dict[str, RoomRect],
    placed: list[LabelBox],
    label_w: float = 60.0,
    label_h: float = 14.0,
) -> float:
    x, y = pos
    score = 0.0
    for room in rooms.values():
        if _rects_overlap(x, y, label_w, label_h, room.x, room.y, room.w, room.h):
            score += 1_000.0
    for lb in placed:
        if _rects_overlap(x, y, label_w, label_h, lb.x, lb.y, lb.w, lb.h):
            score += 500.0
    return score


def _rects_overlap(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    return (
        ax < bx + bw
        and ax + aw > bx
        and ay < by + bh
        and ay + ah > by
    )
