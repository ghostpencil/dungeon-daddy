"""Tests for dungeon_layout.visual_hierarchy_config — VisualHierarchyConfig."""
from dungeon_daddy.map.dungeon_layout.visual_hierarchy_config import VisualHierarchyConfig


# ---------------------------------------------------------------------------
# Cycle 1 — default construction produces correct boolean values
# ---------------------------------------------------------------------------

def test_default_construction_has_expected_flags():
    cfg = VisualHierarchyConfig()
    assert cfg.show_role_debug_labels is False
    assert cfg.emphasize_critical_path is True
    assert cfg.style_secret_connections is True
    assert cfg.style_endpoint_rooms is True
    assert cfg.style_room_roles is True
    assert cfg.enable_shape_grammar is True
    assert cfg.enable_connection_markers is True
    assert cfg.enable_visual_hierarchy_feedback is True


# ---------------------------------------------------------------------------
# Cycle 2 — overriding one flag does not affect the others
# ---------------------------------------------------------------------------

def test_overriding_one_flag_leaves_others_at_default():
    cfg = VisualHierarchyConfig(emphasize_critical_path=False)
    assert cfg.emphasize_critical_path is False
    assert cfg.style_room_roles is True
    assert cfg.enable_visual_hierarchy_feedback is True
    assert cfg.show_role_debug_labels is False


# ---------------------------------------------------------------------------
# Cycle 3 — show_role_debug_labels can be explicitly enabled
# ---------------------------------------------------------------------------

def test_debug_labels_can_be_enabled():
    cfg = VisualHierarchyConfig(show_role_debug_labels=True)
    assert cfg.show_role_debug_labels is True
    assert cfg.style_room_roles is True  # unrelated flag unchanged


# ---------------------------------------------------------------------------
# Cycle 4 — all-off config can be constructed (useful for testing callers)
# ---------------------------------------------------------------------------

def test_all_off_config_is_constructible():
    cfg = VisualHierarchyConfig(
        show_role_debug_labels=False,
        emphasize_critical_path=False,
        style_secret_connections=False,
        style_endpoint_rooms=False,
        style_room_roles=False,
        enable_shape_grammar=False,
        enable_connection_markers=False,
        enable_visual_hierarchy_feedback=False,
    )
    assert cfg.emphasize_critical_path is False
    assert cfg.enable_visual_hierarchy_feedback is False
