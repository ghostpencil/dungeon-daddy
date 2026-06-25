"""Tests for Phase 50 Slice 8 — VnaActionPanel wiring in PlayView."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dungeon_daddy.data.models import SessionState
from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import ActorState, RoomExit
from dungeon_daddy.ui.panels.exit_list_panel import ExitListPanel
from dungeon_daddy.ui.panels.vna_action_panel import VnaActionPanel

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy" / "data" / "migrations"
)


def _save_exit(repo: MemoryRepository, **kw) -> RoomExit:
    defaults = dict(
        exit_id="e1", campaign_id="camp-1",
        from_room_id="r1", to_room_id="r2", level_id="level-1",
        label="North Door", exit_type="door", status="open",
    )
    defaults.update(kw)
    ex = RoomExit(**defaults)
    repo.save_room_exit(ex)
    return ex


def _actor(**kw) -> ActorState:
    defaults = dict(
        actor_id="pc-1", campaign_id="camp-1", actor_type="pc",
        slug="elara", display_name="Elara", status="active",
        actions={"fight": 2, "sense": 1}, playbook_slug="fighter",
    )
    defaults.update(kw)
    return ActorState(**defaults)


def _make_view(tmp_path: Path, actor: ActorState | None = None):
    from dungeon_daddy.views.play_view import PlayView
    from dungeon_daddy.ui.player_action_state import PlayerActionState

    mem_repo = MemoryRepository(tmp_path / "test.duckdb")
    mem_repo.initialize_schema(MIGRATIONS_DIR)
    mem_repo.save_campaign("camp-1", "test-campaign", "Test Campaign")

    actor = actor or _actor()
    view = PlayView.__new__(PlayView)
    view._mem_repo = mem_repo
    view._rpg_campaign_id = "camp-1"
    view._state = SessionState(
        dungeon_id="d1", current_level_idx=0,
        current_room_id="r1", visited_rooms=["r1"],
    )
    view._dungeon = None
    view._rpg_vna = VnaActionPanel()
    view._exit_panel = ExitListPanel()
    view._rpg_action = MagicMock(_actors=[actor])
    view._action_state = PlayerActionState()
    view._action_state.set_actor_roster([actor.actor_id])
    view._chat = MagicMock()
    return view


# ---------------------------------------------------------------------------
# _refresh_vna_panel — populates the panel from the current room/actor
# ---------------------------------------------------------------------------

def test_refresh_vna_panel_populates_universal_verbs(tmp_path):
    view = _make_view(tmp_path)

    view._refresh_vna_panel()

    verbs = {v.verb for v in view._rpg_vna._verbs}
    assert "fight" in verbs
    assert "move" in verbs


def test_refresh_vna_panel_surfaces_exit_as_noun(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", label="North Door", status="open")

    view._refresh_vna_panel()

    noun_ids = {n.noun_id for n in view._rpg_vna._nouns}
    assert "e1" in noun_ids


def test_refresh_vna_panel_feeds_things_here_overlay(tmp_path):
    """Phase 50.6 Slice 7: the same refresh feeds the map overlay, tracking the
    current room — so the overlay updates on load and on every move."""
    from dungeon_daddy.rpg.action_options import RoomThings, SECTION_EXITS
    view = _make_view(tmp_path)
    view._map = MagicMock()
    _save_exit(view._mem_repo, exit_id="e1", label="North Door", status="open")

    view._refresh_vna_panel()

    view._map.set_things_here.assert_called_once()
    things = view._map.set_things_here.call_args.args[0]
    assert isinstance(things, RoomThings)
    assert things.room_id == "r1"
    titles = {s.title for s in things.sections}
    assert SECTION_EXITS in titles
    exit_ids = {t.noun_id for s in things.sections for t in s.things}
    assert "e1" in exit_ids


def test_set_rpg_context_populates_action_builder_on_load(tmp_path):
    # On load the in-chat builder must be ready without first opening the
    # right-panel ACTION tab: set_rpg_context is the chokepoint where mem_repo,
    # actors, and the current room are all finally available, so it refreshes
    # the VNA panel. (_load_player_actors is exercised by its own tests; stub it
    # here to isolate the on-load refresh.)
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", label="North Door", status="open")
    view._load_player_actors = lambda: None
    assert view._rpg_vna._verbs == []  # empty before context attaches

    view.set_rpg_context(view._mem_repo, "camp-1")

    assert view._rpg_vna._verbs  # builder now has its verb options
    assert "e1" in {n.noun_id for n in view._rpg_vna._nouns}


# ---------------------------------------------------------------------------
# _refresh_vna_panel — hidden exits excluded; same-type exits disambiguated
# ---------------------------------------------------------------------------

def _dungeon_with_rooms(rooms):
    from dungeon_daddy.data.models import Dungeon, DungeonMeta, Level, Room

    room_models = [
        Room(id=rid, num=i + 1, name=name, x=x, y=y, w=2, h=2, type="room", note="")
        for i, (rid, name, x, y) in enumerate(rooms)
    ]
    level = Level(
        id=0, name="L1", summary="", ecology="", loop="",
        width=20, height=20, entries=[], rooms=room_models, connections=[],
    )
    meta = DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q")
    return Dungeon(meta=meta, levels=[level])


def test_refresh_vna_panel_excludes_hidden_exit(tmp_path):
    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="open-1", to_room_id="r2", status="open")
    _save_exit(view._mem_repo, exit_id="secret-1", to_room_id="r3", status="hidden")

    view._refresh_vna_panel()

    noun_ids = {n.noun_id for n in view._rpg_vna._nouns}
    assert "open-1" in noun_ids
    assert "secret-1" not in noun_ids


def test_refresh_vna_panel_disambiguates_doors_by_direction(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon = _dungeon_with_rooms([
        ("r1", "Forge Floor", 0, 0),
        ("r2", "Gearworks", 10, 0),   # east of r1
        ("r3", "Stair Landing", 0, 10),  # south of r1
    ])
    _save_exit(view._mem_repo, exit_id="e-east", label="Door", to_room_id="r2", status="open")
    _save_exit(view._mem_repo, exit_id="e-south", label="Door", to_room_id="r3", status="open")

    view._refresh_vna_panel()

    labels = {n.noun_id: n.label for n in view._rpg_vna._nouns}
    assert labels["e-east"] == "Door East"
    assert labels["e-south"] == "Door South"


def _dungeon_with_connected_rooms(rooms, connections):
    from dungeon_daddy.data.models import (
        Connection, Dungeon, DungeonMeta, Level, Room,
    )

    room_models = [
        Room(id=rid, num=i + 1, name=name, x=x, y=y, w=2, h=2, type="room", note="")
        for i, (rid, name, x, y) in enumerate(rooms)
    ]
    conn_models = [Connection(from_room=a, to_room=b, type="hall") for a, b in connections]
    level = Level(
        id=0, name="L1", summary="", ecology="", loop="",
        width=60, height=20, entries=[], rooms=room_models, connections=conn_models,
    )
    meta = DungeonMeta(title="T", theme="t", setting="s", party="p", quest="q")
    return Dungeon(meta=meta, levels=[level])


def test_refresh_vna_panel_directions_follow_rendered_layout_not_raw_coords(tmp_path):
    # All three destinations sit due-east of the hub in raw dungeon coords, so
    # raw geometry would label every door "Door East". The layout pipeline
    # re-grids them around the hub by their connections, spreading them to
    # distinct compass points — the panel must follow that rendered layout
    # (the map the player sees), not the raw coordinates.
    view = _make_view(tmp_path)
    view._dungeon = _dungeon_with_connected_rooms(
        [
            ("r1", "Hub", 0, 0),
            ("rE", "East One", 10, 0),
            ("rE2", "East Two", 20, 0),
            ("rE3", "East Three", 30, 0),
        ],
        [("r1", "rE"), ("r1", "rE2"), ("r1", "rE3")],
    )
    _save_exit(view._mem_repo, exit_id="d1", label="Door", to_room_id="rE", status="open")
    _save_exit(view._mem_repo, exit_id="d2", label="Door", to_room_id="rE2", status="open")
    _save_exit(view._mem_repo, exit_id="d3", label="Door", to_room_id="rE3", status="open")

    view._refresh_vna_panel()

    labels = {n.noun_id: n.label for n in view._rpg_vna._nouns}
    door_labels = [labels["d1"], labels["d2"], labels["d3"]]
    assert door_labels != ["Door East"] * 3  # raw coords would collide here
    assert len(set(door_labels)) == 3  # layout disambiguates all three


def test_refresh_vna_panel_visited_exit_shows_room_name(tmp_path):
    view = _make_view(tmp_path)
    view._dungeon = _dungeon_with_rooms([
        ("r1", "Forge Floor", 0, 0),
        ("r2", "Gearworks", 10, 0),
    ])
    view._state.visited_rooms = ["r1", "r2"]
    _save_exit(view._mem_repo, exit_id="e-east", label="Door", to_room_id="r2", status="open")

    view._refresh_vna_panel()

    labels = {n.noun_id: n.label for n in view._rpg_vna._nouns}
    assert labels["e-east"] == "Door -> Gearworks"


# ---------------------------------------------------------------------------
# _on_vna_submit — routes a resolved Card to the engine
# ---------------------------------------------------------------------------

def test_submit_move_card_moves_party(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", status="open")
    view._map = MagicMock()
    view._rpg_scene = MagicMock()
    view._spawn_dm_thread = MagicMock()
    view._compact_history = MagicMock()
    view._save_session = MagicMock()
    view._dm_history = []

    view._on_vna_submit(ActionCard(verb="move", noun_id="e1", adverb="cautiously"))

    assert view._state.current_room_id == "r2"
    assert "r2" in view._state.visited_rooms


def test_move_refreshes_vna_panel_to_new_room(tmp_path):
    """After the party moves, the VNA noun list reflects the destination room."""
    from dungeon_daddy.rpg.action_options import ActionCard

    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", from_room_id="r1", to_room_id="r2", status="open")
    _save_exit(view._mem_repo, exit_id="e2", from_room_id="r2", to_room_id="r3", status="open")
    view._map = MagicMock()
    view._rpg_scene = MagicMock()
    view._spawn_dm_thread = MagicMock()
    view._compact_history = MagicMock()
    view._save_session = MagicMock()
    view._dm_history = []

    view._on_vna_submit(ActionCard(verb="move", noun_id="e1", adverb="cautiously"))

    noun_ids = {n.noun_id for n in view._rpg_vna._nouns}
    assert view._state.current_room_id == "r2"
    assert "e2" in noun_ids   # destination room's exit is now surfaced
    assert "e1" not in noun_ids  # the room we left is gone


def test_submit_skill_card_posts_mechanical_bubble(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.service import RpgService

    view = _make_view(tmp_path)
    view._rpg_service = RpgService()
    view._dm_agent = None
    view._rpg_debug = None
    view._rpg_char = MagicMock()
    view._rpg_fallout = MagicMock()

    view._on_vna_submit(ActionCard(verb="fight", noun_id="pc-1", adverb="cautiously"))

    assert view._chat.add_message.called
    assert view._chat.add_message.call_args.args[0] == "system"


def test_submit_pickup_card_picks_up_item(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-1", campaign_id="camp-1", slug="gold-coin",
        display_name="Gold Coin", item_type="dungeon_item",
        description="A coin.", room_id="r1", status="active",
    ))

    view._on_vna_submit(ActionCard(verb="pick-up", noun_id="itm-1", adverb="cautiously"))

    picked = next(i for i in view._mem_repo.get_items("camp-1") if i["item_id"] == "itm-1")
    assert picked["owner_actor_id"] == "pc-1"
    assert picked["room_id"] is None


def test_set_acting_actor_syncs_action_state_and_panel(tmp_path):
    """Cycling the CHAR picker makes that PC the actor the ACTION tab acts as."""
    view = _make_view(tmp_path)
    borin = _actor(actor_id="pc-2", slug="borin", display_name="Borin")
    view._rpg_action = MagicMock(_actors=[view._rpg_action._actors[0], borin])
    view._action_state.set_actor_roster(["pc-1", "pc-2"])
    view._rpg_char = MagicMock()

    view._set_acting_actor("pc-2")

    assert view._action_state.actor_id == "pc-2"
    assert view._acting_actor().actor_id == "pc-2"
    assert view._rpg_vna.acting_actor_name() == "Borin"


def test_submit_activate_card_warns_not_wired(tmp_path):
    # Object not in repo → error system message (object-not-found path)
    from dungeon_daddy.rpg.action_options import ActionCard

    view = _make_view(tmp_path)

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-1", adverb="cautiously"))

    assert view._chat.add_message.call_args.args[0] == "system"


def test_submit_activate_card_applies_deterministic_transition(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-lever", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="lever", display_name="Iron Lever", archetype="mechanism",
        description="A heavy lever.", current_state="idle",
        transitions=[
            ObjectTransition(
                transition_id="tr-1", object_id="obj-lever",
                from_state="idle", to_state="pulled",
                trigger="pull", contested=False,
            )
        ],
    ))

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-lever", adverb="cautiously"))

    updated = view._mem_repo.get_room_object("obj-lever")
    assert updated["current_state"] == "pulled"
    msg = view._chat.add_message.call_args.args[1]
    assert "Iron Lever" in msg
    assert "pulled" in msg


def test_submit_activate_deterministic_spawns_dm_narration(tmp_path):
    # Successful deterministic activation injects transition context into DM history
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

    view = _make_view(tmp_path)
    view._dungeon = _dungeon_with_rooms([("r1", "Forge Floor", 0, 0)])
    view._spawn_dm_thread = MagicMock()
    view._compact_history = MagicMock()
    view._dm_history = []
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-lever", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="lever", display_name="Iron Lever", archetype="mechanism",
        description="A heavy lever.", current_state="idle",
        transitions=[ObjectTransition(
            transition_id="tr-1", object_id="obj-lever",
            from_state="idle", to_state="pulled", trigger="pull", contested=False,
        )],
    ))

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-lever", adverb="cautiously"))

    assert view._spawn_dm_thread.called
    sent = " ".join(m.content for m in view._dm_history)
    assert "Iron Lever" in sent
    assert "pulled" in sent


def test_submit_activate_card_posts_roll_bubble_for_contested_transition(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import ObjectTransition, RoomObject
    from dungeon_daddy.rpg.service import RpgService

    view = _make_view(tmp_path)
    view._rpg_service = RpgService()
    view._dm_agent = None
    view._rpg_debug = None
    view._rpg_char = MagicMock()
    view._rpg_fallout = MagicMock()
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-trap", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="trap", display_name="Pressure Trap", archetype="mechanism",
        description="A dangerous trap.", current_state="armed",
        transitions=[
            ObjectTransition(
                transition_id="tr-2", object_id="obj-trap",
                from_state="armed", to_state="triggered",
                trigger="disarm", contested=True, action_verb="fight",
            )
        ],
    ))

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-trap", adverb="cautiously"))

    assert view._chat.add_message.called
    msg = view._chat.add_message.call_args.args[1]
    assert "rolls" in msg  # mechanical roll bubble, not "not wired" message
    # Roll path → object state unchanged
    updated = view._mem_repo.get_room_object("obj-trap")
    assert updated["current_state"] == "armed"


def test_submit_activate_card_posts_error_when_no_valid_transition(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-stuck", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="stuck-door", display_name="Stuck Door", archetype="structure",
        description="A stuck door.", current_state="stuck",
        # no transitions from "stuck" state
    ))

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-stuck", adverb="cautiously"))

    assert view._chat.add_message.called
    msg = view._chat.add_message.call_args.args[1]
    assert "⚠" in msg


def test_submit_activate_with_required_item_missing_posts_error(tmp_path):
    # transition.requires_item_slug set but actor holds nothing → error, state unchanged
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import ObjectTransition, RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-lift", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="great-lift", display_name="Great Lift", archetype="mechanism",
        description="A massive lift.", current_state="idle",
        transitions=[
            ObjectTransition(
                transition_id="tr-lift", object_id="obj-lift",
                from_state="idle", to_state="powered",
                trigger="power", contested=False,
                requires_item_slug="lift-fuse",
            )
        ],
    ))

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-lift", adverb="cautiously"))

    msg = view._chat.add_message.call_args.args[1]
    assert "⚠" in msg
    assert "lift-fuse" in msg
    updated = view._mem_repo.get_room_object("obj-lift")
    assert updated["current_state"] == "idle"


def test_submit_activate_with_required_item_held_transitions_and_consumes(tmp_path):
    # transition.requires_item_slug set and actor holds it → state changes + item consumed
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-fuse", campaign_id="camp-1", slug="lift-fuse",
        display_name="Lift Fuse", item_type="dungeon_item",
        description="A fuse.", owner_actor_id="pc-1", status="active",
    ))
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-lift", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="great-lift", display_name="Great Lift", archetype="mechanism",
        description="A massive lift.", current_state="idle",
        transitions=[
            ObjectTransition(
                transition_id="tr-lift", object_id="obj-lift",
                from_state="idle", to_state="powered",
                trigger="power", contested=False,
                requires_item_slug="lift-fuse",
            )
        ],
    ))

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-lift", adverb="cautiously"))

    updated = view._mem_repo.get_room_object("obj-lift")
    assert updated["current_state"] == "powered"
    items = view._mem_repo.get_items_by_actor("pc-1")
    fuse = next((i for i in items if i["item_id"] == "itm-fuse"), None)
    assert fuse is not None
    assert fuse["status"] == "consumed"


def test_submit_use_on_object_routes_as_activate(tmp_path):
    # use [fuse] on [lift] with target SOURCE_OBJECT → same activation path as activate [lift]
    from dungeon_daddy.rpg.action_options import ActionCard, NounOption, SOURCE_OBJECT
    from dungeon_daddy.rpg.models import Item, ObjectTransition, RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-fuse", campaign_id="camp-1", slug="lift-fuse",
        display_name="Lift Fuse", item_type="dungeon_item",
        description="A fuse.", owner_actor_id="pc-1", status="active",
    ))
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-lift", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="great-lift", display_name="Great Lift", archetype="mechanism",
        description="A massive lift.", current_state="idle",
        transitions=[
            ObjectTransition(
                transition_id="tr-lift", object_id="obj-lift",
                from_state="idle", to_state="powered",
                trigger="power", contested=False,
                requires_item_slug="lift-fuse",
            )
        ],
    ))
    # plant an object noun so _on_vna_submit can identify the target source
    view._rpg_vna._nouns = [
        NounOption(noun_id="itm-fuse", label="Lift Fuse", target_type="item", slug="lift-fuse", source="carried_item"),
        NounOption(noun_id="obj-lift", label="Great Lift", target_type="object", slug="great-lift", source=SOURCE_OBJECT),
    ]

    view._on_vna_submit(ActionCard(
        verb="use", noun_id="itm-fuse", adverb="cautiously", target_id="obj-lift",
    ))

    updated = view._mem_repo.get_room_object("obj-lift")
    assert updated["current_state"] == "powered"
    fuse = next(i for i in view._mem_repo.get_items("camp-1") if i["item_id"] == "itm-fuse")
    assert fuse["status"] == "consumed"


# ---------------------------------------------------------------------------
# _refresh_vna_panel — the acting actor's carried items surface as nouns
# (so the Equip verb has something to target)
# ---------------------------------------------------------------------------

def test_refresh_vna_panel_surfaces_carried_item_as_noun(tmp_path):
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-eq", campaign_id="camp-1", slug="iron-sword",
        display_name="Iron Sword", item_type="equipped_gear",
        description="A blade.", owner_actor_id="pc-1", status="active",
    ))

    view._refresh_vna_panel()

    nouns = {n.noun_id: n for n in view._rpg_vna._nouns}
    assert "itm-eq" in nouns
    assert nouns["itm-eq"].source == "carried_item"


# ---------------------------------------------------------------------------
# _resolve_vna_roll — the skill-action message sent to the DM names the noun
# (otherwise the LLM cannot narrate what was acted upon)
# ---------------------------------------------------------------------------

def test_skill_card_names_noun_in_dm_message(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import RoomObject
    from dungeon_daddy.rpg.service import RpgService

    view = _make_view(tmp_path)
    view._dungeon = _dungeon_with_rooms([("r1", "Forge Floor", 0, 0)])
    view._rpg_service = RpgService()
    view._dm_agent = None
    view._rpg_debug = None
    view._rpg_char = MagicMock()
    view._rpg_fallout = MagicMock()
    view._spawn_dm_thread = MagicMock()
    view._compact_history = MagicMock()
    view._dm_history = []
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-board", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="notice-board", display_name="Warden's Notice Board",
        archetype="lore_fixture", description="Posted writ.", current_state="default",
    ))
    view._refresh_vna_panel()  # populate the panel's noun list

    view._on_vna_submit(ActionCard(verb="study", noun_id="obj-board", adverb="cautiously"))

    sent = " ".join(m.content for m in view._dm_history)
    assert "Warden's Notice Board" in sent


# ---------------------------------------------------------------------------
# Slice 8 — look verb: read-only description fetch, no roll, no state change
# ---------------------------------------------------------------------------

def test_look_verb_surfaces_in_available_verbs(tmp_path):
    from dungeon_daddy.rpg.action_options import available_verbs

    verbs = {v.verb for v in available_verbs([])}
    assert "look" in verbs


def test_submit_look_card_posts_object_description(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-notice", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="notice-board", display_name="Notice Board",
        archetype="lore_fixture", description="A board with wanted posters.",
        current_state="default",
    ))

    view._on_vna_submit(ActionCard(verb="look", noun_id="obj-notice", adverb="cautiously"))

    assert view._chat.add_message.called
    msg = view._chat.add_message.call_args.args[1]
    assert "wanted posters" in msg


def test_submit_look_card_posts_item_description(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    view._mem_repo.save_item(Item(
        item_id="itm-scroll", campaign_id="camp-1", slug="ancient-scroll",
        display_name="Ancient Scroll", item_type="dungeon_item",
        description="Faded runes warn of the lift's price.",
        room_id="r1", status="active",
    ))

    view._on_vna_submit(ActionCard(verb="look", noun_id="itm-scroll", adverb="cautiously"))

    msg = view._chat.add_message.call_args.args[1]
    assert "lift's price" in msg


def test_submit_look_card_no_state_change(tmp_path):
    """look verb must not alter repo state."""
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import RoomObject

    view = _make_view(tmp_path)
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-jar", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="clay-jar", display_name="Clay Jar",
        archetype="container", description="A sealed clay jar.",
        current_state="sealed",
    ))

    view._on_vna_submit(ActionCard(verb="look", noun_id="obj-jar", adverb="cautiously"))

    obj = view._mem_repo.get_room_object("obj-jar")
    assert obj["current_state"] == "sealed"


def test_give_target_includes_other_party_members(tmp_path):
    """Other party PCs (from _rpg_action._actors) appear as give targets."""
    from dungeon_daddy.rpg.action_options import ActionCard
    from dungeon_daddy.rpg.models import Item

    borin = _actor(actor_id="pc-2", slug="borin", display_name="Borin")
    view = _make_view(tmp_path)
    # Two-member party: default actor (pc-1) + Borin (pc-2)
    view._rpg_action = MagicMock(_actors=[view._rpg_action._actors[0], borin])
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-1", campaign_id="camp-1", slug="ration",
        display_name="Iron Ration", item_type="dungeon_item",
        description="A day's food.", owner_actor_id="pc-1", status="active",
    ))

    view._refresh_vna_panel()
    view._rpg_vna.select_verb("give")

    target_ids = {n.noun_id for n in view._rpg_vna._targets}
    assert "pc-2" in target_ids
    assert "pc-1" not in target_ids  # acting actor excluded from own give targets


def test_use_item_on_locked_exit_routes_to_exit_move(tmp_path):
    """Using a carried item on a locked exit calls _on_exit_move with the exit id."""
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", status="locked")
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-key", campaign_id="camp-1", slug="warden-key",
        display_name="Warden Key", item_type="dungeon_item",
        description="Opens the iron gate.", owner_actor_id="pc-1", status="active",
    ))

    view._refresh_vna_panel()
    view._rpg_vna.select_verb("use")
    view._rpg_vna.select_noun("itm-key")
    view._rpg_vna.select_target("e1")
    view._rpg_vna.select_adverb("cautiously")
    card = view._rpg_vna.build_card()

    view._on_exit_move = MagicMock()
    view._on_vna_submit(card)

    view._on_exit_move.assert_called_once_with("e1", "cautiously", item_slug="warden-key")


def test_use_item_on_exit_passes_item_slug_to_exit_move_when_no_key_match(tmp_path):
    """Item slug is forwarded to _on_exit_move when it doesn't match exit's key requirement."""
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    # Exit requires a different key — so item slug does NOT match; party still moves
    _save_exit(view._mem_repo, exit_id="e1", status="open",
               requires_item_slug="other-key")
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-key", campaign_id="camp-1", slug="rusty-key",
        display_name="Rusty Key", item_type="dungeon_item",
        description="Some key.", owner_actor_id="pc-1", status="active",
    ))

    view._refresh_vna_panel()
    view._rpg_vna.select_verb("use")
    view._rpg_vna.select_noun("itm-key")
    view._rpg_vna.select_target("e1")
    view._rpg_vna.select_adverb("cautiously")
    card = view._rpg_vna.build_card()

    view._on_exit_move = MagicMock()
    view._on_vna_submit(card)

    call_kwargs = view._on_exit_move.call_args
    assert call_kwargs.kwargs.get("item_slug") == "rusty-key"


def test_use_matching_key_on_exit_clears_requires_item_slug(tmp_path):
    """When item slug matches exit's requires_item_slug: DB cleared, party stays, message posted."""
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", status="open",
               requires_item_slug="lift-warden-key")
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-key", campaign_id="camp-1", slug="lift-warden-key",
        display_name="Lift Warden's Iron Key", item_type="dungeon_item",
        description="Opens the lift.", owner_actor_id="pc-1", status="active",
    ))

    view._refresh_vna_panel()
    view._rpg_vna.select_verb("use")
    view._rpg_vna.select_noun("itm-key")
    view._rpg_vna.select_target("e1")
    view._rpg_vna.select_adverb("cautiously")
    card = view._rpg_vna.build_card()

    view._on_exit_move = MagicMock()
    view._on_vna_submit(card)

    row = view._mem_repo.get_exit_by_id("e1")
    assert row["requires_item_slug"] is None
    view._on_exit_move.assert_not_called()
    view._chat.add_message.assert_any_call("system", "North Door: unlocked.")  # lock glyph stripped


def test_use_non_matching_item_on_exit_does_not_clear_requires_item_slug(tmp_path):
    """When item slug does not match exit's requires_item_slug, the slug is preserved."""
    from dungeon_daddy.rpg.models import Item

    view = _make_view(tmp_path)
    _save_exit(view._mem_repo, exit_id="e1", status="open",
               requires_item_slug="lift-warden-key")
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_item(Item(
        item_id="itm-key", campaign_id="camp-1", slug="rusty-key",
        display_name="Rusty Key", item_type="dungeon_item",
        description="Some other key.", owner_actor_id="pc-1", status="active",
    ))

    view._refresh_vna_panel()
    view._rpg_vna.select_verb("use")
    view._rpg_vna.select_noun("itm-key")
    view._rpg_vna.select_target("e1")
    view._rpg_vna.select_adverb("cautiously")
    card = view._rpg_vna.build_card()

    view._on_exit_move = MagicMock()
    view._on_vna_submit(card)

    row = view._mem_repo.get_exit_by_id("e1")
    assert row["requires_item_slug"] == "lift-warden-key"


def test_build_context_bundle_includes_current_room_objects(tmp_path):
    """The DM context bundle carries the current room's objects (with text)."""
    from dungeon_daddy.rpg.models import RoomObject
    from dungeon_daddy.rpg.service import RpgService

    view = _make_view(tmp_path)
    view._rpg_service = RpgService()
    view._rpg_debug = None
    view._mem_repo.save_actor("pc-1", "camp-1", "pc", "elara", "Elara", "active", room_id="r1")
    view._mem_repo.save_room_object(RoomObject(
        object_id="obj-board", campaign_id="camp-1", room_id="r1", level_id="level-1",
        slug="notice-board", display_name="Warden's Notice Board",
        archetype="lore_fixture", description="The lift-key stays at the watch-stall.",
        current_state="default",
    ))

    bundle = view._build_context_bundle()

    objects = bundle.current_room.get("objects", [])
    names = [o["display_name"] for o in objects]
    assert "Warden's Notice Board" in names
    assert any("watch-stall" in o["description"] for o in objects)
