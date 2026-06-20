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


def test_submit_activate_card_warns_not_wired(tmp_path):
    from dungeon_daddy.rpg.action_options import ActionCard

    view = _make_view(tmp_path)

    view._on_vna_submit(ActionCard(verb="activate", noun_id="obj-1", adverb="cautiously"))

    assert view._chat.add_message.call_args.args[0] == "system"
