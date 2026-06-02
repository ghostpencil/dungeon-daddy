"""Atmosphere layer specification for Graph Mode. Pure data — no arcade dependency."""
from __future__ import annotations

from dataclasses import dataclass

from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig

_FRAME_COLOR = (60, 80, 100, 160)
_TICK_COLOR = (70, 90, 110, 120)


@dataclass
class AtmosphereSpec:
    enabled: bool
    vignette_alpha: int
    vignette_bands: int
    frame_color: tuple[int, int, int, int]
    frame_width: float
    frame_inset: float
    show_corner_ticks: bool
    corner_tick_size: float
    corner_tick_color: tuple[int, int, int, int]


_DISABLED = AtmosphereSpec(
    enabled=False,
    vignette_alpha=0,
    vignette_bands=0,
    frame_color=(0, 0, 0, 0),
    frame_width=0.0,
    frame_inset=0.0,
    show_corner_ticks=False,
    corner_tick_size=0.0,
    corner_tick_color=(0, 0, 0, 0),
)

_DEFAULT = AtmosphereSpec(
    enabled=True,
    vignette_alpha=0,
    vignette_bands=0,
    frame_color=_FRAME_COLOR,
    frame_width=1.5,
    frame_inset=4.0,
    show_corner_ticks=True,
    corner_tick_size=12.0,
    corner_tick_color=_TICK_COLOR,
)


def build_atmosphere_spec(config: GraphPresentationConfig | None = None) -> AtmosphereSpec:
    """Return a deterministic atmosphere specification derived from the presentation config."""
    cfg = config or GraphPresentationConfig()
    return _DEFAULT if cfg.enable_atmosphere else _DISABLED
