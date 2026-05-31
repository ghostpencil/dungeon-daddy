"""Unit tests for GraphViewState — camera + interaction state model."""
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState


class TestHoverRoom:
    def test_set_hovered_room(self):
        state = GraphViewState()
        state.hover_room("R1")
        assert state.hovered_room_id == "R1"

    def test_clear_hovered_room(self):
        state = GraphViewState()
        state.hover_room("R1")
        state.hover_room(None)
        assert state.hovered_room_id is None


class TestSelectRoom:
    def test_set_selected_room(self):
        state = GraphViewState()
        state.select_room("R2")
        assert state.selected_room_id == "R2"

    def test_replace_selected_room(self):
        state = GraphViewState()
        state.select_room("R1")
        state.select_room("R3")
        assert state.selected_room_id == "R3"

    def test_clear_selected_room(self):
        state = GraphViewState()
        state.select_room("R1")
        state.select_room(None)
        assert state.selected_room_id is None


class TestHoverConnection:
    def test_set_hovered_connection(self):
        state = GraphViewState()
        state.hover_connection("R1→R2")
        assert state.hovered_connection_id == "R1→R2"

    def test_clear_hovered_connection(self):
        state = GraphViewState()
        state.hover_connection("R1→R2")
        state.hover_connection(None)
        assert state.hovered_connection_id is None


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


class TestDefaultConstruction:
    def test_all_fields_are_null_or_default(self):
        state = GraphViewState()
        assert state.selected_room_id is None
        assert state.hovered_room_id is None
        assert state.hovered_connection_id is None
        assert state.camera.pan_x == 0.0
        assert state.camera.pan_y == 0.0
        assert state.camera.zoom == 1.0
