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
    from dungeon_daddy.rpg.action_options import ActionCard

    view = _make_view(tmp_path)

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-1", adverb="cautiously"))

    assert view._chat.add_message.call_args.args[0] == "system"


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
