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
    border_color: tuple[int, int, int]
    fill_alpha: int
    fill_color: tuple[int, int, int]
    size_bias: float
    shape_type: str
    show_marker: bool
    marker_text: str | None
    priority: str
    glow_alpha: int = 0
    has_second_outline: bool = False


# Default neutral colors used when no role-specific color is defined.
_DEFAULT_BORDER = (100, 120, 140)
_DEFAULT_FILL = (30, 35, 45)

_DEFAULT = GraphRoomStyle(
    key="unknown",
    border_width=1.0,
    border_alpha=200,
    border_color=_DEFAULT_BORDER,
    fill_alpha=40,
    fill_color=_DEFAULT_FILL,
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
            border_color=(140, 160, 180),
            fill_alpha=45,
            fill_color=(28, 38, 50),
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
        border_color=(70, 75, 90),
        fill_alpha=20,
        fill_color=(20, 22, 32),
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
        border_color=(70, 130, 200),   # blue
        fill_alpha=55,
        fill_color=(25, 40, 65),
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
        border_color=(60, 180, 160),   # teal
        fill_alpha=50,
        fill_color=(22, 48, 45),
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
        border_color=(200, 60, 60),    # red
        fill_alpha=70,
        fill_color=(55, 20, 20),
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
        border_color=(200, 170, 60),   # gold
        fill_alpha=60,
        fill_color=(50, 42, 15),
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
        border_color=(190, 160, 60),   # amber
        fill_alpha=50,
        fill_color=(45, 38, 15),
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
        border_color=(160, 130, 80),
        fill_alpha=50,
        fill_color=(38, 30, 18),
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
        border_color=(200, 170, 60),   # gold
        fill_alpha=55,
        fill_color=(48, 40, 12),
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
        border_color=(210, 100, 40),   # orange
        fill_alpha=50,
        fill_color=(55, 25, 15),       # dark brownish-red
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
        border_color=_DEFAULT_BORDER,
        fill_alpha=30,
        fill_color=_DEFAULT_FILL,
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
        border_color=(100, 120, 155),
        fill_alpha=35,
        fill_color=(28, 32, 48),
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
        border_color=(160, 110, 60),
        fill_alpha=40,
        fill_color=(40, 28, 18),
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
        border_color=_DEFAULT_BORDER,
        fill_alpha=30,
        fill_color=_DEFAULT_FILL,
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
        border_color=(90, 105, 120),
        fill_alpha=25,
        fill_color=(25, 28, 38),
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
        border_color=_DEFAULT_BORDER,
        fill_alpha=30,
        fill_color=_DEFAULT_FILL,
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
        border_color=(120, 140, 165),
        fill_alpha=40,
        fill_color=_DEFAULT_FILL,
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
        border_color=(100, 120, 150),
        fill_alpha=30,
        fill_color=(28, 32, 45),
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
