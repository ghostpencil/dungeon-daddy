"""Unit tests for GraphViewState — camera + interaction state model."""
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState


class TestClearSelection:
    def test_clear_selection_resets_selected_room(self):
        state = GraphViewState()
        state.select_room("R4")
        state.clear_selection()
        assert state.selected_room_id is None

    def test_clear_selection_leaves_hover_intact(self):
        state = GraphViewState()
        state.select_room("R4")
        state.hover_room("R5")
        state.clear_selection()
        assert state.hovered_room_id == "R5"


class TestRecenter:
    def test_recenter_resets_pan_and_zoom(self):
        state = GraphViewState()
        state.camera.pan_x = 150.0
        state.camera.pan_y = -80.0
        state.camera.zoom = 2.5
        state.recenter()
        assert state.camera.pan_x == 0.0
        assert state.camera.pan_y == 0.0
        assert state.camera.zoom == 1.0

    def test_recenter_does_not_clear_selection(self):
        state = GraphViewState()
        state.select_room("R3")
        state.recenter()
        assert state.selected_room_id == "R3"
