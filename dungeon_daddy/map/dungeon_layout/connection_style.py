"""Visual style resolution for Graph Mode connections.

Maps a connection label string to a GraphConnectionStyle descriptor.
No Arcade dependency — pure Python.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GraphConnectionStyle:
    key: str
    line_width: float
    alpha: int
    dashed: bool
    marker_type: str | None
    priority: str


_DEFAULT = GraphConnectionStyle(
    key="normal",
    line_width=1.5,
    alpha=200,
    dashed=False,
    marker_type=None,
    priority="low",
)

_STYLES: dict[str, GraphConnectionStyle] = {
    "locked": GraphConnectionStyle(
        key="locked",
        line_width=2.5,
        alpha=220,
        dashed=False,
        marker_type="lock",
        priority="high",
    ),
    "secret": GraphConnectionStyle(
        key="secret",
        line_width=1.0,
        alpha=120,
        dashed=True,
        marker_type=None,
        priority="low",
    ),
    "shortcut": GraphConnectionStyle(
        key="shortcut",
        line_width=1.0,
        alpha=140,
        dashed=True,
        marker_type=None,
        priority="low",
    ),
    "vertical": GraphConnectionStyle(
        key="vertical",
        line_width=1.5,
        alpha=200,
        dashed=False,
        marker_type="vertical",
        priority="medium",
    ),
    "hazard": GraphConnectionStyle(
        key="hazard",
        line_width=2.0,
        alpha=220,
        dashed=False,
        marker_type="hazard",
        priority="medium",
    ),
    "impossible": GraphConnectionStyle(
        key="impossible",
        line_width=1.0,
        alpha=100,
        dashed=True,
        marker_type=None,
        priority="low",
    ),
    "pursuit": GraphConnectionStyle(
        key="pursuit",
        line_width=1.5,
        alpha=160,
        dashed=True,
        marker_type=None,
        priority="medium",
    ),
}

_ALIASES: dict[str, str] = {
    "hole": "vertical",
    "secret_shortcut": "secret",
    "lock_key": "locked",
}


class GraphConnectionStyleResolver:
    def resolve(self, label: str) -> GraphConnectionStyle:
        canonical = _ALIASES.get(label, label)
        return _STYLES.get(canonical, _DEFAULT)
