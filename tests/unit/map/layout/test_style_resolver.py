"""Tests for dungeon_layout.style_resolver — interaction style resolution pipeline."""
from dungeon_daddy.map.dungeon_layout.graph_view_state import GraphViewState
from dungeon_daddy.map.dungeon_layout.room_style import GraphRoomStyleResolver
from dungeon_daddy.map.dungeon_layout.style_resolver import resolve_room_render_style


def _base(role: str = "hub"):
    return GraphRoomStyleResolver().resolve(role)


# ---------------------------------------------------------------------------
# Cycle 1 — default state: no selection, no hover → style unchanged
# ---------------------------------------------------------------------------

def test_default_state_returns_role_style_unchanged():
    base = _base("hub")
    state = GraphViewState()
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    assert result.border_alpha == base.border_alpha
    assert result.fill_alpha == base.fill_alpha
    assert result.border_width == base.border_width
    assert result.border_color == base.border_color


# ---------------------------------------------------------------------------
# Cycle 2 — hover state: higher alpha and wider border
# ---------------------------------------------------------------------------

def test_hover_state_brightens_border_and_widens():
    base = _base("hall")  # border_alpha=180, fill_alpha=30 — room to brighten
    state = GraphViewState()
    state.hover_room("R1")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    assert result.border_alpha > base.border_alpha
    assert result.fill_alpha > base.fill_alpha
    assert result.border_width > base.border_width


# ---------------------------------------------------------------------------
# Cycle 3 — hover does NOT apply when room is selected (selected wins)
# ---------------------------------------------------------------------------

def test_hover_suppressed_when_room_is_selected():
    base = _base("hall")
    state = GraphViewState()
    state.hover_room("R1")
    state.select_room("R1")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    # Selected styling dominates: bright white-blue border, not a hover-bumped alpha
    assert result.border_color == (220, 220, 255)
    assert result.border_alpha == 255
    assert result.border_width == base.border_width + 2.0


# ---------------------------------------------------------------------------
# Cycle 4 — selected state: thick border, bright color, boosted fill alpha
# ---------------------------------------------------------------------------

def test_selected_state_dominant_style():
    base = _base("entrance")  # border_alpha=230, fill_alpha=50
    state = GraphViewState()
    state.select_room("R1")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    assert result.border_width == base.border_width + 2.0
    assert result.border_alpha == 255
    assert result.border_color == (220, 220, 255)
    assert result.fill_alpha == min(255, base.fill_alpha + 30)


# ---------------------------------------------------------------------------
# Cycle 5 — focus/fade: unrelated room fades when another room is selected
# ---------------------------------------------------------------------------

def test_unrelated_room_fades_when_another_selected():
    base = _base("hall")  # border_alpha=180, fill_alpha=30
    state = GraphViewState()
    state.select_room("R2")  # different room selected
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),  # R1 not connected to R2
    )
    assert result.border_alpha < base.border_alpha
    assert result.fill_alpha < base.fill_alpha


# ---------------------------------------------------------------------------
# Cycle 6 — connected room gets neighbor highlight
# ---------------------------------------------------------------------------

def test_connected_room_gets_neighbor_highlight():
    base = _base("hall")  # border_alpha=180, fill_alpha=30
    state = GraphViewState()
    state.select_room("R2")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids={"R1"},  # R1 is a neighbor of the selected room
    )
    assert result.border_alpha > base.border_alpha
    assert result.fill_alpha > base.fill_alpha
    assert result.border_width > base.border_width


# ---------------------------------------------------------------------------
# Cycle 7 — critical path room gets only subtle fade, not full fade
# ---------------------------------------------------------------------------

def test_critical_path_room_gets_subtle_fade_not_full_fade():
    base = _base("hall")  # border_alpha=180, fill_alpha=30
    state = GraphViewState()
    state.select_room("R2")
    result_crit = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids={"R1"},
        connected_room_ids=set(),
    )
    result_unrelated = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    # Critical path room fades less than a fully unrelated room
    assert result_crit.border_alpha > result_unrelated.border_alpha
    # fill_alpha is unchanged for critical path room (not faded)
    assert result_crit.fill_alpha == base.fill_alpha


# ---------------------------------------------------------------------------
# Cycle 8 — focus/fade does NOT apply to the selected room itself
# ---------------------------------------------------------------------------

def test_selected_room_not_faded_by_focus_mode():
    base = _base("entrance")  # fill_alpha=50
    state = GraphViewState()
    state.select_room("R1")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    # Selected room must not be faded — fill_alpha should be boosted, not reduced
    assert result.fill_alpha >= base.fill_alpha
    assert result.border_color == (220, 220, 255)


# ---------------------------------------------------------------------------
# Cycle 9 — selected room on critical path → other crit-path rooms emphasised
# ---------------------------------------------------------------------------

def test_critical_path_room_emphasized_when_selected_room_is_on_critical_path():
    base = _base("hall")  # border_alpha=180, fill_alpha=30, border_width=2.0
    state = GraphViewState()
    state.select_room("R2")  # R2 is selected AND on the critical path
    result = resolve_room_render_style(
        room_id="R1",  # R1 is also on the critical path but not selected/connected
        base_style=base,
        view_state=state,
        critical_path_room_ids={"R1", "R2"},  # both rooms on critical path
        connected_room_ids=set(),  # R1 is NOT directly connected to R2
    )
    # Critical path room should be emphasised (brighter + thicker), not faded
    assert result.border_alpha > base.border_alpha
    assert result.border_width > base.border_width


# ---------------------------------------------------------------------------
# Cycle 10 — selected room NOT on critical path → crit-path rooms still fade
# ---------------------------------------------------------------------------

def test_critical_path_room_still_fades_when_selected_room_not_on_critical_path():
    base = _base("hall")  # border_alpha=180
    state = GraphViewState()
    state.select_room("R3")  # R3 selected, NOT on critical path
    result = resolve_room_render_style(
        room_id="R1",  # R1 is on critical path but not connected to R3
        base_style=base,
        view_state=state,
        critical_path_room_ids={"R1", "R2"},  # R3 not included
        connected_room_ids=set(),
    )
    # Without critical-path selection, existing subtle fade applies
    assert result.border_alpha < base.border_alpha


# ---------------------------------------------------------------------------
# Cycle 11 — non-critical non-connected room still fades when selected on crit
# ---------------------------------------------------------------------------

def test_unrelated_room_still_fades_when_selected_room_is_on_critical_path():
    base = _base("hall")  # border_alpha=180, fill_alpha=30
    state = GraphViewState()
    state.select_room("R2")  # R2 on critical path
    result = resolve_room_render_style(
        room_id="R3",  # R3 is NOT on critical path, NOT connected
        base_style=base,
        view_state=state,
        critical_path_room_ids={"R1", "R2"},  # R3 absent
        connected_room_ids=set(),
    )
    # Unrelated rooms must still fade regardless of critical-path selection
    assert result.border_alpha < base.border_alpha
    assert result.fill_alpha < base.fill_alpha


# ---------------------------------------------------------------------------
# Cycle 12 — GraphRoomStyle has glow_alpha=0 and has_second_outline=False by default
# ---------------------------------------------------------------------------

def test_graph_room_style_default_glow_and_outline_fields():
    base = _base("hub")
    assert base.glow_alpha == 0
    assert base.has_second_outline is False


# ---------------------------------------------------------------------------
# Cycle 13 — hover border width is base + 1.0 (stronger than old +0.5)
# ---------------------------------------------------------------------------

def test_hover_border_width_is_base_plus_one():
    base = _base("hall")
    state = GraphViewState()
    state.hover_room("R1")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    assert result.border_width == base.border_width + 1.0


# ---------------------------------------------------------------------------
# Cycle 14 — hover sets glow_alpha > 0 (visible outer glow)
# ---------------------------------------------------------------------------

def test_hover_sets_glow_alpha():
    base = _base("hall")
    state = GraphViewState()
    state.hover_room("R1")
    result = resolve_room_render_style(
        room_id="R1",
        base_style=base,
        view_state=state,
        critical_path_room_ids=set(),
        connected_room_ids=set(),
    )
    assert result.glow_alpha > 0


# ---------------------------------------------------------------------------
# Cycle 15 — selected glow_alpha > hover glow_alpha (stronger emphasis)
# ---------------------------------------------------------------------------

def test_selected_glow_stronger_than_hover_glow():
    base = _base("hall")

    hover_state = GraphViewState()
    hover_state.hover_room("R1")
    hover_result = resolve_room_render_style(
        room_id="R1", base_style=base, view_state=hover_state,
        critical_path_room_ids=set(), connected_room_ids=set(),
    )

    sel_state = GraphViewState()
    sel_state.select_room("R1")
    sel_result = resolve_room_render_style(
        room_id="R1", base_style=base, view_state=sel_state,
        critical_path_room_ids=set(), connected_room_ids=set(),
    )

    assert sel_result.glow_alpha > hover_result.glow_alpha


# ---------------------------------------------------------------------------
# Cycle 16 — selected sets has_second_outline=True
# ---------------------------------------------------------------------------

def test_selected_sets_has_second_outline():
    base = _base("hall")
    state = GraphViewState()
    state.select_room("R1")
    result = resolve_room_render_style(
        room_id="R1", base_style=base, view_state=state,
        critical_path_room_ids=set(), connected_room_ids=set(),
    )
    assert result.has_second_outline is True


def test_hover_does_not_set_second_outline():
    base = _base("hall")
    state = GraphViewState()
    state.hover_room("R1")
    result = resolve_room_render_style(
        room_id="R1", base_style=base, view_state=state,
        critical_path_room_ids=set(), connected_room_ids=set(),
    )
    assert result.has_second_outline is False
