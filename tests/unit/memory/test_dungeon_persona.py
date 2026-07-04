from pathlib import Path

from dungeon_daddy.memory.dungeon_persona import (
    read_dungeon_knowledge,
    read_dungeon_voice,
    write_dungeon_knowledge,
    write_dungeon_voice,
)


class TestDungeonVoiceRoundTrip:
    def test_write_then_read_returns_voice_text(self, tmp_path: Path) -> None:
        voice = "I am the Crucible. I have waited eons for warmth."
        path = write_dungeon_voice(tmp_path, "camp-1", voice)
        assert read_dungeon_voice(path) == voice

    def test_missing_file_reads_as_none(self, tmp_path: Path) -> None:
        assert read_dungeon_voice(tmp_path / "voice.md") is None


class TestDungeonKnowledgeRoundTrip:
    def test_write_then_read_returns_secrets_list(self, tmp_path: Path) -> None:
        secrets = [
            "The eastern seal is cracked.",
            "Pinion remembers the first warden.",
        ]
        path = write_dungeon_knowledge(tmp_path, "camp-1", secrets)
        assert read_dungeon_knowledge(path) == secrets

    def test_empty_knowledge_round_trips_to_empty_list(self, tmp_path: Path) -> None:
        path = write_dungeon_knowledge(tmp_path, "camp-1", [])
        assert read_dungeon_knowledge(path) == []

    def test_secrets_with_punctuation_round_trip(self, tmp_path: Path) -> None:
        secrets = [
            "The warden's name — long forgotten — is Ys.",
            "Rule: never speak the third seal aloud.",
        ]
        path = write_dungeon_knowledge(tmp_path, "camp-1", secrets)
        assert read_dungeon_knowledge(path) == secrets

    def test_missing_file_reads_as_empty_list(self, tmp_path: Path) -> None:
        assert read_dungeon_knowledge(tmp_path / "knowledge.md") == []
