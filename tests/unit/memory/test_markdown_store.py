from pathlib import Path

import pytest

from dungeon_daddy.memory.markdown_store import (
    compute_checksum,
    read_memory,
    validate_front_matter,
    write_memory,
)


class TestWriteMemory:
    def test_creates_file_starting_with_delimiter(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        write_memory(path, {"id": "m1", "type": "note"}, "# Body")
        assert path.read_text(encoding="utf-8").startswith("---\n")

    def test_front_matter_keys_present_in_file(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        write_memory(path, {"id": "m1", "type": "fallout", "severity": "moderate"}, "")
        text = path.read_text(encoding="utf-8")
        assert "id:" in text
        assert "severity:" in text


class TestReadMemory:
    def test_round_trips_front_matter(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        fm = {"id": "m1", "type": "note", "campaign_id": "c1", "updated_at": "2026-06-02"}
        write_memory(path, fm, "# Body text")
        recovered_fm, body = read_memory(path)
        assert recovered_fm["id"] == "m1"
        assert recovered_fm["type"] == "note"
        assert recovered_fm["campaign_id"] == "c1"

    def test_round_trips_body(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        write_memory(path, {"id": "x"}, "# Heading\n\nSome content.")
        _, body = read_memory(path)
        assert "# Heading" in body
        assert "Some content." in body

    def test_empty_body_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        write_memory(path, {"id": "x"}, "")
        _, body = read_memory(path)
        assert body == ""

    def test_raises_on_missing_delimiter(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.md"
        path.write_text("no front matter here", encoding="utf-8")
        with pytest.raises(ValueError, match="front matter"):
            read_memory(path)


class TestComputeChecksum:
    def test_returns_hex_string(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        write_memory(path, {"id": "x"}, "body")
        cs = compute_checksum(path)
        assert isinstance(cs, str)
        assert len(cs) == 64  # SHA-256 hex

    def test_same_file_returns_same_checksum(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.md"
        write_memory(path, {"id": "x"}, "body")
        assert compute_checksum(path) == compute_checksum(path)

    def test_different_content_returns_different_checksum(self, tmp_path: Path) -> None:
        p1 = tmp_path / "a.md"
        p2 = tmp_path / "b.md"
        write_memory(p1, {"id": "a"}, "body a")
        write_memory(p2, {"id": "b"}, "body b")
        assert compute_checksum(p1) != compute_checksum(p2)


class TestValidateFrontMatter:
    def test_passes_with_all_required_fields(self) -> None:
        validate_front_matter(
            {"id": "x", "type": "note", "campaign_id": "c", "updated_at": "2026-06-02"}
        )

    def test_raises_on_missing_id(self) -> None:
        with pytest.raises(ValueError, match="id"):
            validate_front_matter({"type": "note", "campaign_id": "c", "updated_at": "x"})

    def test_raises_on_missing_type(self) -> None:
        with pytest.raises(ValueError, match="type"):
            validate_front_matter({"id": "x", "campaign_id": "c", "updated_at": "x"})

    def test_raises_on_missing_campaign_id(self) -> None:
        with pytest.raises(ValueError, match="campaign_id"):
            validate_front_matter({"id": "x", "type": "note", "updated_at": "x"})

    def test_raises_on_missing_updated_at(self) -> None:
        with pytest.raises(ValueError, match="updated_at"):
            validate_front_matter({"id": "x", "type": "note", "campaign_id": "c"})

    def test_extra_fields_pass_validation(self) -> None:
        validate_front_matter(
            {
                "id": "x",
                "type": "fallout",
                "campaign_id": "c",
                "updated_at": "2026-06-02",
                "severity": "moderate",
                "extra_custom_field": "ok",
            }
        )
