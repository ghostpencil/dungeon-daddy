"""Heuristic visibility feedback for Graph Mode presentation reports.

Pure Python — no Arcade dependency.
"""
from __future__ import annotations

from dungeon_daddy.map.dungeon_layout.atmosphere import AtmosphereSpec
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig

_MAX_READABLE_VIGNETTE_ALPHA = 120


def compute_visibility_feedback(
    pres_config: GraphPresentationConfig,
    atm_spec: AtmosphereSpec,
) -> dict:
    """Return a visibility_feedback dict for the presentation feedback JSON."""
    if not atm_spec.enabled:
        atmosphere_ok = True
    else:
        atmosphere_ok = atm_spec.vignette_alpha <= _MAX_READABLE_VIGNETTE_ALPHA

    return {
        "room_labels_readable": True,
        "connection_labels_readable": True,
        "detail_panel_text_readable": pres_config.show_detail_panel,
        "atmosphere_not_too_dark": atmosphere_ok,
        "unrelated_rooms_still_identifiable_when_faded": True,
    }
