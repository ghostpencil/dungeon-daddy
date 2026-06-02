from dataclasses import dataclass


@dataclass
class GraphPresentationConfig:
    show_detail_panel: bool = True
    show_role_markers: bool = True
    show_connection_markers: bool = True
    enable_atmosphere: bool = True
    enable_hover_glow: bool = True
    enable_selection_glow: bool = True
    fade_unrelated_on_selection: bool = True
    detail_panel_position: str = "right"
