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
    assert panel._how_chips == []


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
# set_how_chips — stores the contextual chip row
# ---------------------------------------------------------------------------

def test_set_how_chips_stores_chips():
    from dungeon_daddy.ui.how_chips import build_how_chips
    panel = _panel()
    chips = build_how_chips(one_way=True)
    panel.set_how_chips(chips)
    assert [c.how for c in panel._how_chips] == [c.how for c in chips]


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

# ---------------------------------------------------------------------------
# Interaction — how-chip selection + click-to-move
# ---------------------------------------------------------------------------

def _interactive_panel():
    from dungeon_daddy.ui.how_chips import build_how_chips
    panel = _panel()
    panel.set_from_context({
        "visible_exits": [
            {"exit_id": "e-north", "label": "North Door", "status": "open", "exit_type": "door"},
            {"exit_id": "e-east", "label": "East Arch", "status": "open", "exit_type": "arch"},
        ],
        "locked_exits": [],
        "hidden_exit_hint": 0,
    })
    panel.set_how_chips(build_how_chips())
    panel.setup(0.0, 0.0, 240.0, 360.0)
    return panel


def test_default_selected_how_is_first_chip():
    panel = _interactive_panel()
    assert panel.selected_how == "cautiously"


def test_clicking_chip_changes_selected_how():
    panel = _interactive_panel()
    layout = panel._layout()
    _, _, (cx, cy, cw, ch) = next(c for c in layout["chips"] if c[0] == "boldly")
    handled = panel.handle_click(cx + cw / 2, cy + ch / 2)
    assert handled is True
    assert panel.selected_how == "boldly"


def test_clicking_exit_invokes_move_callback_with_selected_how():
    panel = _interactive_panel()
    moves: list[tuple[str, str]] = []
    panel.set_move_callback(lambda exit_id, how: moves.append((exit_id, how)))

    layout = panel._layout()
    _, _, _, (ex, ey, ew, eh) = next(e for e in layout["exits"] if e[0] == "e-east")
    handled = panel.handle_click(ex + ew / 2, ey + eh / 2)

    assert handled is True
    assert moves == [("e-east", "cautiously")]


def test_clicking_empty_space_returns_false():
    panel = _interactive_panel()
    panel.set_move_callback(lambda exit_id, how: (_ for _ in ()).throw(AssertionError("should not move")))
    assert panel.handle_click(1000.0, 1000.0) is False


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
