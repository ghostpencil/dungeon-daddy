from __future__ import annotations

from pathlib import Path

import pytest

from dungeon_daddy.memory.repository import MemoryRepository
from dungeon_daddy.rpg.models import RoomExit

MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "dungeon_daddy"
    / "data"
    / "migrations"
)

CAMPAIGN_ID = "campaign:test"
ROOM_A = "room:a"
EXIT_ID = "exit:door-1"


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    r = MemoryRepository(tmp_path / "test.duckdb")
    r.initialize_schema(MIGRATIONS_DIR)
    yield r
    r.close()


def _make_exit(exit_id: str = EXIT_ID, status: str = "locked") -> RoomExit:
    return RoomExit(
        exit_id=exit_id,
        campaign_id=CAMPAIGN_ID,
        from_room_id=ROOM_A,
        to_room_id="room:b",
        level_id="level:1",
        label="North Door",
        status=status,
    )


# ---------------------------------------------------------------------------
# Slice 8-1: unlock_exit flips locked → open and returns accepted
# ---------------------------------------------------------------------------

def test_unlock_exit_flips_locked_to_open(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.unlock_exit import unlock_exit

    repo.save_room_exit(_make_exit(status="locked"))

    result = unlock_exit(EXIT_ID, CAMPAIGN_ID, repo)

    assert result.accepted is True
    row = repo.get_exit_by_id(EXIT_ID)
    assert row["status"] == "open"


# ---------------------------------------------------------------------------
# Slice 8-2: unlock_exit emits exit.unlocked domain event
# ---------------------------------------------------------------------------

def test_unlock_exit_emits_domain_event(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.unlock_exit import unlock_exit

    repo.save_room_exit(_make_exit(status="locked"))

    result = unlock_exit(EXIT_ID, CAMPAIGN_ID, repo)

    assert len(result.events) == 1
    assert result.events[0].event_type == "exit.unlocked"
    assert result.events[0].payload["exit_id"] == EXIT_ID


# ---------------------------------------------------------------------------
# Slice 8-3: unlock_exit rejects a non-locked exit
# ---------------------------------------------------------------------------

def test_unlock_exit_rejects_open_exit(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.unlock_exit import unlock_exit

    repo.save_room_exit(_make_exit(status="open"))

    result = unlock_exit(EXIT_ID, CAMPAIGN_ID, repo)

    assert result.accepted is False
    assert result.rejection_reason is not None
    assert repo.get_exit_by_id(EXIT_ID)["status"] == "open"


# ---------------------------------------------------------------------------
# Slice 8-4: unlock_exit rejects an unknown exit_id
# ---------------------------------------------------------------------------

def test_unlock_exit_rejects_unknown_exit(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.unlock_exit import unlock_exit

    result = unlock_exit("exit:nonexistent", CAMPAIGN_ID, repo)

    assert result.accepted is False
    assert result.rejection_reason is not None


# ---------------------------------------------------------------------------
# Slice 8-5: seal_exit flips one_way → sealed and emits exit.sealed
# ---------------------------------------------------------------------------

def test_seal_exit_flips_one_way_to_sealed(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.unlock_exit import seal_exit

    repo.save_room_exit(_make_exit(status="one_way"))

    result = seal_exit(EXIT_ID, CAMPAIGN_ID, repo)

    assert result.accepted is True
    assert repo.get_exit_by_id(EXIT_ID)["status"] == "sealed"
    assert len(result.events) == 1
    assert result.events[0].event_type == "exit.sealed"
    assert result.events[0].payload["exit_id"] == EXIT_ID


# ---------------------------------------------------------------------------
# Slice 8-6: seal_exit rejects a non-one_way exit
# ---------------------------------------------------------------------------

def test_seal_exit_rejects_open_exit(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.unlock_exit import seal_exit

    repo.save_room_exit(_make_exit(status="open"))

    result = seal_exit(EXIT_ID, CAMPAIGN_ID, repo)

    assert result.accepted is False
    assert result.rejection_reason is not None
    assert repo.get_exit_by_id(EXIT_ID)["status"] == "open"


# ---------------------------------------------------------------------------
# Slice 8-7: BlockExitChange is a valid ProposedChange (parses in proposal)
# ---------------------------------------------------------------------------

def test_block_exit_change_parses_in_proposal() -> None:
    from dungeon_daddy.rpg.proposal import LLMReactionProposal

    raw = {
        "narration_hint": "The passage collapses behind you.",
        "proposed_changes": [
            {"kind": "block_exit", "exit_id": EXIT_ID, "reason": "Ceiling collapsed."}
        ],
    }

    proposal = LLMReactionProposal.model_validate(raw)

    assert len(proposal.proposed_changes) == 1
    change = proposal.proposed_changes[0]
    assert change.kind == "block_exit"
    assert change.exit_id == EXIT_ID


# ---------------------------------------------------------------------------
# Slice 8-8: validate_proposal rejects BlockExitChange with unknown exit_id
# ---------------------------------------------------------------------------

def test_validate_proposal_rejects_block_exit_unknown_id() -> None:
    from dungeon_daddy.rpg.proposal import BlockExitChange, LLMReactionProposal
    from dungeon_daddy.rpg.proposal_validator import validate_proposal

    proposal = LLMReactionProposal(
        narration_hint="Collapse.",
        proposed_changes=[BlockExitChange(exit_id="exit:unknown", reason="Collapsed.")],
    )

    result = validate_proposal(proposal, known_clock_ids=set(), known_exit_ids={"exit:real"})

    assert len(result.rejected) == 1
    assert result.rejected[0].change.kind == "block_exit"


def test_validate_proposal_accepts_block_exit_known_id() -> None:
    from dungeon_daddy.rpg.proposal import BlockExitChange, LLMReactionProposal
    from dungeon_daddy.rpg.proposal_validator import validate_proposal

    proposal = LLMReactionProposal(
        narration_hint="Collapse.",
        proposed_changes=[BlockExitChange(exit_id=EXIT_ID, reason="Collapsed.")],
    )

    result = validate_proposal(proposal, known_clock_ids=set(), known_exit_ids={EXIT_ID})

    assert len(result.accepted) == 1
    assert result.accepted[0].kind == "block_exit"


# ---------------------------------------------------------------------------
# Slice 8-9: apply_low_risk_proposals with BlockExitChange blocks the exit
# ---------------------------------------------------------------------------

def test_apply_block_exit_sets_status_blocked_and_emits_event(repo: MemoryRepository) -> None:
    from dungeon_daddy.rpg.proposal import BlockExitChange, LLMReactionProposal
    from dungeon_daddy.rpg.proposal_applier import apply_low_risk_proposals
    from dungeon_daddy.rpg.proposal_validator import ValidationResult

    repo.save_room_exit(_make_exit(status="open"))

    change = BlockExitChange(exit_id=EXIT_ID, reason="Ceiling collapsed.")
    validation_result = ValidationResult(accepted=[change])

    apply_result = apply_low_risk_proposals(validation_result, repo, CAMPAIGN_ID)

    assert repo.get_exit_by_id(EXIT_ID)["status"] == "blocked"
    event_types = [e.event_type for e in apply_result.events]
    assert "exit.blocked" in event_types
