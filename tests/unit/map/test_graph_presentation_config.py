from dungeon_daddy.map.dungeon_layout.graph_presentation_config import GraphPresentationConfig


def test_defaults_all_enabled():
    cfg = GraphPresentationConfig()
    assert cfg.show_detail_panel is True
    assert cfg.show_role_markers is True
    assert cfg.show_connection_markers is True
    assert cfg.enable_atmosphere is True
    assert cfg.enable_hover_glow is True
    assert cfg.enable_selection_glow is True
    assert cfg.fade_unrelated_on_selection is True
    assert cfg.detail_panel_position == "right"


def test_can_disable_detail_panel():
    cfg = GraphPresentationConfig(show_detail_panel=False)
    assert cfg.show_detail_panel is False
    assert cfg.show_role_markers is True  # others unchanged


def test_can_disable_atmosphere():
    cfg = GraphPresentationConfig(enable_atmosphere=False)
    assert cfg.enable_atmosphere is False
    assert cfg.enable_hover_glow is True  # others unchanged


def test_can_disable_markers():
    cfg = GraphPresentationConfig(show_role_markers=False, show_connection_markers=False)
    assert cfg.show_role_markers is False
    assert cfg.show_connection_markers is False
    assert cfg.show_detail_panel is True  # others unchanged
