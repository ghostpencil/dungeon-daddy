from __future__ import annotations


def _panel():
    from dungeon_daddy.ui.panels.exit_list_panel import ExitListPanel
    return ExitListPanel()


# ---------------------------------------------------------------------------
# Init — empty
# ---------------------------------------------------------------------------

def test_empty_on_init():
    panel = _panel()
    assert panel._visible_exits == []
    assert panel._locked_exits == []
    assert panel._hidden_exit_hint == 0


# ---------------------------------------------------------------------------
# set_from_context — unpacks a build_room_context() bundle
# ---------------------------------------------------------------------------

def test_set_from_context_unpacks_bundle():
    panel = _panel()
    bundle = {
        "room_id": "r1",
        "resonance_point": False,
        "visible_exits": [
            {"label": "North Door", "status": "open", "exit_type": "door"},
        ],
        "locked_exits": [
            {"label": "Spiral Stair", "status": "locked",
             "reason": "locked", "missing_condition": "iron-key"},
        ],
        "hidden_exit_hint": 1,
        "visited_rooms": ["r1"],
    }
    panel.set_from_context(bundle)
    assert panel._visible_exits[0]["label"] == "North Door"
    assert panel._locked_exits[0]["missing_condition"] == "iron-key"
    assert panel._hidden_exit_hint == 1


# ---------------------------------------------------------------------------
# setup — stores geometry
# ---------------------------------------------------------------------------

def test_setup_stores_geometry():
    panel = _panel()
    panel.setup(10.0, 20.0, 200.0, 300.0)
    assert (panel._x, panel._y, panel._w, panel._h) == (10.0, 20.0, 200.0, 300.0)


# ---------------------------------------------------------------------------
# draw — renders exit labels, locked reasons, hidden hint (arcade mocked)
# ---------------------------------------------------------------------------

def test_set_current_room_renders_name_and_id(mocker):
    import arcade
    mocker.patch.object(arcade, "draw_rect_filled")
    mocker.patch.object(arcade, "draw_rect_outline")
    draw_text = mocker.patch.object(arcade, "draw_text")

    panel = _panel()
    panel.set_current_room("Trap Room", "R5")
    panel.set_from_context({"visible_exits": [], "locked_exits": [], "hidden_exit_hint": 0})
    panel.setup(0.0, 0.0, 220.0, 320.0)
    panel.draw()

    rendered = " | ".join(str(c.args[0]) for c in draw_text.call_args_list)
    assert "Trap Room" in rendered
    assert "R5" in rendered


def test_draw_renders_labels_and_hint(mocker):
    import arcade
    mocker.patch.object(arcade, "draw_rect_filled")
    draw_text = mocker.patch.object(arcade, "draw_text")

    panel = _panel()
    panel.set_from_context({
        "visible_exits": [{"exit_id": "e1", "label": "North Door", "status": "open", "exit_type": "door"}],
        "locked_exits": [{"label": "Spiral Stair", "status": "locked",
                          "reason": "locked", "missing_condition": "iron-key"}],
        "hidden_exit_hint": 1,
    })
    panel.setup(0.0, 0.0, 220.0, 320.0)
    panel.draw()

    rendered = " | ".join(str(c.args[0]) for c in draw_text.call_args_list)
    assert "North Door" in rendered
    assert "Spiral Stair" in rendered and "iron-key" in rendered
    assert "1 hidden exit detected" in rendered
