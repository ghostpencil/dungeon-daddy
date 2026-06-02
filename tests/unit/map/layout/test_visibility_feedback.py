"""Tests for visibility_feedback — heuristic readability checks for Graph Mode."""
from dungeon_daddy.map.dungeon_layout.atmosphere import AtmosphereSpec, build_atmosphere_spec
from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig
from dungeon_daddy.map.dungeon_layout.visibility_feedback import compute_visibility_feedback


def _dark_atm() -> AtmosphereSpec:
    """Atmosphere spec with vignette_alpha above the readable threshold."""
    spec = build_atmosphere_spec()
    return AtmosphereSpec(
        enabled=True,
        vignette_alpha=150,
        vignette_bands=spec.vignette_bands,
        frame_color=spec.frame_color,
        frame_width=spec.frame_width,
        frame_inset=spec.frame_inset,
        show_corner_ticks=spec.show_corner_ticks,
        corner_tick_size=spec.corner_tick_size,
        corner_tick_color=spec.corner_tick_color,
    )


def _disabled_atm() -> AtmosphereSpec:
    from dungeon_daddy.map.dungeon_layout.atmosphere import _DISABLED  # noqa: PLC0415
    return _DISABLED


# ---------------------------------------------------------------------------
# Cycle 1 — Default config: all fields True
# ---------------------------------------------------------------------------

def test_default_config_all_fields_true():
    config = GraphPresentationConfig()
    atm = build_atmosphere_spec(config)
    result = compute_visibility_feedback(config, atm)

    assert result["room_labels_readable"] is True
    assert result["connection_labels_readable"] is True
    assert result["detail_panel_text_readable"] is True
    assert result["atmosphere_not_too_dark"] is True
    assert result["unrelated_rooms_still_identifiable_when_faded"] is True


# ---------------------------------------------------------------------------
# Cycle 2 — Panel hidden: detail_panel_text_readable is False
# ---------------------------------------------------------------------------

def test_panel_hidden_makes_detail_panel_not_readable():
    config = GraphPresentationConfig(show_detail_panel=False)
    atm = build_atmosphere_spec(config)
    result = compute_visibility_feedback(config, atm)

    assert result["detail_panel_text_readable"] is False


# ---------------------------------------------------------------------------
# Cycle 3 — Dark atmosphere: atmosphere_not_too_dark is False
# ---------------------------------------------------------------------------

def test_dark_atmosphere_flags_not_too_dark_as_false():
    config = GraphPresentationConfig()
    result = compute_visibility_feedback(config, _dark_atm())

    assert result["atmosphere_not_too_dark"] is False


# ---------------------------------------------------------------------------
# Cycle 4 — Disabled atmosphere: atmosphere_not_too_dark is True regardless
# ---------------------------------------------------------------------------

def test_disabled_atmosphere_is_never_too_dark():
    config = GraphPresentationConfig(enable_atmosphere=False)
    result = compute_visibility_feedback(config, _disabled_atm())

    assert result["atmosphere_not_too_dark"] is True


# ---------------------------------------------------------------------------
# Cycle 5 — No fading: unrelated rooms still identifiable (full visibility)
# ---------------------------------------------------------------------------

def test_no_fade_unrelated_rooms_still_identifiable():
    config = GraphPresentationConfig(fade_unrelated_on_selection=False)
    atm = build_atmosphere_spec(config)
    result = compute_visibility_feedback(config, atm)

    assert result["unrelated_rooms_still_identifiable_when_faded"] is True
