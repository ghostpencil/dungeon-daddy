#!/usr/bin/env python3
"""Regenerates the entry table in dev_diary/README.md from diary files."""

import re
from datetime import datetime
from pathlib import Path

DIARY_DIR = Path(__file__).parent.parent / "dev_diary"
README = DIARY_DIR / "README.md"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")
MARKER_START = "<!-- DIARY_INDEX_START -->"
MARKER_END = "<!-- DIARY_INDEX_END -->"


def format_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%b')} {dt.day}"


def read_entry_meta(path: Path) -> tuple[str, str]:
    """Returns (title, focus) by reading the H1 and Focus: lines."""
    title = ""
    focus = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not title and line.startswith("# "):
            parts = line.split(" - ", 1)
            title = parts[1].strip() if len(parts) > 1 else line[2:].strip()
        if not focus and line.startswith("Focus:"):
            focus = line[len("Focus:"):].strip()
        if title and focus:
            break
    return title, focus


def build_table(entries: list[dict]) -> str:
    rows = [
        "| # | Date | Entry | Focus |",
        "|---|------|-------|-------|",
    ]
    for i, e in enumerate(entries, 1):
        rows.append(
            f"| {i} | {e['date']} | [{e['title']}]({e['filename']}) | {e['focus']} |"
        )
    return "\n".join(rows)


def main() -> None:
    entries = []
    for path in sorted(DIARY_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        date_str, _ = m.groups()
        title, focus = read_entry_meta(path)
        entries.append({
            "filename": path.name,
            "date": format_date(date_str),
            "title": title,
            "focus": focus,
        })

    content = README.read_text(encoding="utf-8")
    start_idx = content.index(MARKER_START) + len(MARKER_START)
    end_idx = content.index(MARKER_END)
    new_content = content[:start_idx] + "\n" + build_table(entries) + "\n" + content[end_idx:]
    README.write_text(new_content, encoding="utf-8")
    print(f"diary index: {len(entries)} entries written")


if __name__ == "__main__":
    main()
