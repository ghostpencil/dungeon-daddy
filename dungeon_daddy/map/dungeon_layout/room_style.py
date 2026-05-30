"""Visual style resolution for Graph Mode rooms.

Maps a RoomRole to a GraphRoomStyle descriptor.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.map.dungeon_layout.semantics import RoomRole


@dataclass
class GraphRoomStyle:
    key: str
    border_width: float
    border_alpha: int
    fill_alpha: int
    size_bias: float
    shape_type: str
    show_marker: bool
    marker_text: str | None
    priority: str


_DEFAULT = GraphRoomStyle(
    key="unknown",
    border_width=1.0,
    border_alpha=200,
    fill_alpha=40,
    size_bias=1.0,
    shape_type="rectangle",
    show_marker=False,
    marker_text=None,
    priority="low",
)

_STYLES: dict[str, GraphRoomStyle] = {
    **{
        role: GraphRoomStyle(
            key=role,
            border_width=2.0,
            border_alpha=220,
            fill_alpha=45,
            size_bias=0.9,
            shape_type="rectangle",
            show_marker=True,
            marker_text="↓" if role in ("descent", "stairs", "elevator") else "EXIT",
            priority="medium",
        )
        for role in ("exit", "descent", "elevator", "stairs")
    },
    "secret": GraphRoomStyle(
        key="secret",
        border_width=1.0,
        border_alpha=100,
        fill_alpha=20,
        size_bias=0.85,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "hub": GraphRoomStyle(
        key="hub",
        border_width=2.5,
        border_alpha=255,
        fill_alpha=55,
        size_bias=1.25,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="high",
    ),
    "entrance": GraphRoomStyle(
        key="entrance",
        border_width=2.0,
        border_alpha=230,
        fill_alpha=50,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=True,
        marker_text="IN",
        priority="medium",
    ),
    "boss": GraphRoomStyle(
        key="boss",
        border_width=3.0,
        border_alpha=255,
        fill_alpha=70,
        size_bias=1.3,
        shape_type="rectangle",
        show_marker=True,
        marker_text="BOSS",
        priority="high",
    ),
    "objective": GraphRoomStyle(
        key="objective",
        border_width=2.5,
        border_alpha=255,
        fill_alpha=60,
        size_bias=1.2,
        shape_type="rectangle",
        show_marker=True,
        marker_text="OBJ",
        priority="high",
    ),
    "key_room": GraphRoomStyle(
        key="key_room",
        border_width=2.0,
        border_alpha=220,
        fill_alpha=50,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=True,
        marker_text="KEY",
        priority="medium",
    ),
    "lock_room": GraphRoomStyle(
        key="lock_room",
        border_width=2.5,
        border_alpha=240,
        fill_alpha=50,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=True,
        marker_text="LCK",
        priority="medium",
    ),
    "treasure": GraphRoomStyle(
        key="treasure",
        border_width=1.5,
        border_alpha=210,
        fill_alpha=55,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="medium",
    ),
    "hazard": GraphRoomStyle(
        key="hazard",
        border_width=2.0,
        border_alpha=240,
        fill_alpha=50,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=True,
        marker_text="!",
        priority="medium",
    ),
    "hall": GraphRoomStyle(
        key="hall",
        border_width=1.0,
        border_alpha=180,
        fill_alpha=30,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "library": GraphRoomStyle(
        key="library",
        border_width=1.0,
        border_alpha=190,
        fill_alpha=35,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "forge": GraphRoomStyle(
        key="forge",
        border_width=1.5,
        border_alpha=200,
        fill_alpha=40,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "utility": GraphRoomStyle(
        key="utility",
        border_width=1.0,
        border_alpha=180,
        fill_alpha=30,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "corridor": GraphRoomStyle(
        key="corridor",
        border_width=1.0,
        border_alpha=170,
        fill_alpha=25,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "side_room": GraphRoomStyle(
        key="side_room",
        border_width=1.0,
        border_alpha=180,
        fill_alpha=30,
        size_bias=0.9,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
    "transition": GraphRoomStyle(
        key="transition",
        border_width=1.5,
        border_alpha=200,
        fill_alpha=40,
        size_bias=1.0,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="medium",
    ),
    "study": GraphRoomStyle(
        key="study",
        border_width=1.0,
        border_alpha=180,
        fill_alpha=30,
        size_bias=0.85,
        shape_type="rectangle",
        show_marker=False,
        marker_text=None,
        priority="low",
    ),
}


class GraphRoomStyleResolver:
    def resolve(self, role: RoomRole) -> GraphRoomStyle:
        return _STYLES.get(role, _DEFAULT)
