# Data Model

All models live in `dungeon_daddy/data/models.py`.
All are Pydantic `BaseModel` subclasses unless stated otherwise.

---

## Serialization Rules

- Save: `dungeon.model_dump(mode="json")` → `json.dumps(..., indent=2)`
- Load: `Dungeon.model_validate(json.loads(raw_text))`
- The JSON on disk must be human-readable and pretty-printed (indent=2).
- Field names in JSON match Python field names exactly, except where a
  `Field(alias=...)` is specified (see `Connection`).

---

## Models

### `LoopPattern`

Describes a cyclic dungeon design pattern. Loaded from a bundled JSON catalog
(not user-editable). Nine patterns ship with the app — see `spec/FEATURES.md`.

```python
class LoopPattern(BaseModel):
    key: str                    # unique identifier, e.g. "lock_key"
    name: str                   # display name, e.g. "Lock & Key"
    blurb: str                  # one-sentence description for the UI card
    path_a_length: str          # "short" | "long" | "equal"
    path_b_length: str          # "short" | "long" | "equal" | "short (secret)" | "short (one-way)"
    beats: list[str]            # narrative waypoints e.g. ["entry", "locked door", ...]
                                # Displayed in the loop card mini-cycle diagram in the
                                # Inspector Loops tab, and passed to DungeonWizardAgent
                                # as context when explaining pattern options to the GM.
    source: str                 # "Dormans" | "Sersa Victory" | "Alexandrian"
```

---

### `Loop`

A concrete loop instance applied to a level. Assigns rooms to path A and path B.

```python
class Loop(BaseModel):
    id: str                     # unique within the dungeon, e.g. "L1-main"
    pattern: str                # key of the LoopPattern used
    note: str                   # designer note explaining this specific loop
    entry: str                  # room id of the cycle entry point
    goal: str                   # room id of the cycle goal
    path_a: list[str]           # ordered list of room ids for path A (teal)
    path_b: list[str]           # ordered list of room ids for path B (violet)
```

---

### `Room`

A single room on a dungeon level. Position and size are in grid cells.

```python
class Room(BaseModel):
    id: str                     # unique within level, e.g. "1-A", "2-C"
    num: int                    # display number shown on map
    name: str                   # short name e.g. "Flooded Entry"
    x: int                      # grid column of top-left corner
    y: int                      # grid row of top-left corner
    w: int                      # width in cells
    h: int                      # height in cells
    type: str                   # "hall" | "shrine" | "lair" | "vault" | "stair" | "study" | "boss"
    note: str                   # GM-facing description paragraph
```

---

### `Connection`

A directional link between two rooms. Bidirectional connections are stored once.

```python
class Connection(BaseModel):
    from_room: str = Field(alias="from")   # source room id
    to_room: str = Field(alias="to")       # destination room id
    type: str       # "door" | "hall" | "arch" | "hole" | "stair_down" | "stair_up"
    note: str = ""  # optional annotation e.g. "Sigil-locked"

    model_config = ConfigDict(populate_by_name=True)
```

When serialising to JSON, use `model_dump(by_alias=True)` so the file contains
`"from"` and `"to"` (matching the web prototype format).

---

### `Entry`

A staircase or external access point. Drawn as a marker on the map, not a Room.

```python
class Entry(BaseModel):
    x: float                    # grid column (can be fractional for edge positions)
    y: float                    # grid row
    type: str                   # "stair_up" | "stair_down"
    label: str                  # e.g. "Entrance", "From L1"
```

---

### `Level`

One floor of the dungeon.

```python
class Level(BaseModel):
    id: int                     # 1-indexed
    name: str                   # e.g. "The Sunken Vestibule"
    summary: str                # one-line situation summary for GM
    ecology: str                # monsters/NPCs present
    loop: str                   # prose description of the level's loop concept
    loops: list[Loop] = []      # concrete loop instances (first = primary)
    width: int                  # grid columns
    height: int                 # grid rows
    entries: list[Entry]        # stair/access markers
    rooms: list[Room]
    connections: list[Connection]
```

---

### `DungeonMeta`

Top-level dungeon metadata.

```python
class DungeonMeta(BaseModel):
    schema_version: str = "1.0" # incremented when the model changes
    title: str                  # e.g. "Tomb of the Forgotten King"
    theme: str                  # e.g. "Undead • Necromantic"
    setting: str                # prose description of location and history
    party: str                  # e.g. "4 adventurers • level 3 • mixed"
    quest: str                  # the primary quest hook
```

`schema_version` allows future migrations. When loading a file, if
`schema_version` does not match the current version, `DungeonRepository`
should log a warning but still attempt to load (Pydantic will use defaults
for any newly added fields). Breaking migrations require a version bump and
a migration function — document these in `data/migrations.py` when needed.

---

### `Dungeon`

Root object. One file on disk = one Dungeon.

```python
class Dungeon(BaseModel):
    meta: DungeonMeta
    levels: list[Level]
    loop_patterns: dict[str, LoopPattern] = {}
```

`loop_patterns` is embedded in the dungeon file so the file is self-contained
and playable without the app's bundled catalog. The app merges its built-in
patterns with any patterns stored in the dungeon.

---

### `ChatMessage`

A single message in a **persisted** chat transcript (design or play).
Used only for saving/loading session history — not for API transport.

```python
from typing import Literal

class ChatMessage(BaseModel):
    role: Literal["gm", "dm", "system"]
    content: str    # the message text
```

**`ChatMessage` vs `LLMMessage`:** These are distinct types with different purposes.

| Type | Module | Purpose |
|---|---|---|
| `ChatMessage` | `data/models.py` | Persisted transcript entries (saved to JSON) |
| `LLMMessage` | `llm/provider.py` | API transport (sent to the LLM provider) |

When building an API call from chat history, convert `ChatMessage` → `LLMMessage`:
only include `role="gm"` (→ `"user"`) and `role="dm"` (→ `"assistant"`) messages.
Exclude `role="system"` dividers — they are display-only.

---

### `SessionState`

Tracks the runtime state of a play session. Saved alongside the dungeon.

```python
class SessionState(BaseModel):
    dungeon_id: str                             # filename stem of the dungeon
    current_level_idx: int = 0
    current_room_id: str | None = None          # None = not yet set; initialised to first room on load
    visited_rooms: list[str] = []
    map_variant: str = "grid"                   # "grid" | "tiles" | "graph"
    active_loop_id: str | None = None
    play_transcript: list[ChatMessage] = []
    design_transcript: list[ChatMessage] = []
```

**`current_room_id` contract:**
- `None` means no session has started yet (new dungeon, never played).
- On load, if `current_room_id` is `None`, `PlayView` must set it to
  `dungeon.levels[0].rooms[0].id` before rendering.
- An empty string `""` is **not** a valid state and must never be serialised.

**Transcript persistence:**
- Both `play_transcript` and `design_transcript` are persisted inside `SessionState`
  (the `_session.json` file), **not** in the dungeon file itself.
- `DungeonRepository.save_session()` is called:
  - After every chat message sent by the user (immediate persistence, no data loss on crash).
  - On mode switch.
  - On explicit File → Save.
- On startup, `DungeonRepository.load_session()` is called after `load()`. If it
  returns `None` (no session file), a fresh `SessionState` is constructed with
  `dungeon_id` set to the dungeon stem and all other fields at defaults.

SessionState is saved as `<dungeon_stem>_session.json` next to the dungeon file.

---

### `ValidationResult`

Returned by the dungeon validator (see FEATURES.md F-16c). Defined as a plain
dataclass in `dungeon_daddy/data/models.py` alongside the Pydantic models.
It is never serialised to JSON — it is a runtime-only result object.

```python
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)  # one human-readable string per failed rule

    def __bool__(self) -> bool:
        return self.is_valid
```

Usage:

```python
def validate_dungeon(dungeon: Dungeon) -> ValidationResult:
    """Run all validation rules. Returns a ValidationResult."""
    errors = []
    for level in dungeon.levels:
        _check_connectivity(level, errors)
        _check_loop_room_references(level, errors)
        _check_grid_bounds(level, errors)
        _check_no_self_connections(level, errors)
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

`validate_dungeon()` lives in `dungeon_daddy/data/models.py` as a module-level
function, not a method on `Dungeon`, to keep models free of domain logic.

---

### `LoopPatternCatalog`

A thin wrapper used to load/validate the built-in pattern catalog from a bundled
JSON file (`dungeon_daddy/data/loop_patterns.json`).

```python
import importlib.resources
import json

class LoopPatternCatalog(BaseModel):
    patterns: dict[str, LoopPattern]

    @classmethod
    def load_bundled(cls) -> "LoopPatternCatalog":
        """
        Load the built-in loop pattern catalog bundled with the package.
        Uses importlib.resources so this works whether the package is installed
        or run from source.
        """
        pkg_files = importlib.resources.files("dungeon_daddy.data")
        raw = (pkg_files / "loop_patterns.json").read_text(encoding="utf-8")
        return cls.model_validate({"patterns": json.loads(raw)})
```

The bundled file lives at `dungeon_daddy/data/loop_patterns.json`.
`load_sample()` in `DungeonRepository` uses the same pattern:

```python
def load_sample(self) -> Dungeon:
    pkg_files = importlib.resources.files("dungeon_daddy.data")
    raw = (pkg_files / "samples" / "tomb_of_the_forgotten_king.json").read_text(encoding="utf-8")
    return Dungeon.model_validate(json.loads(raw))
```

---

## Repository Interface

`DungeonRepository` in `dungeon_daddy/data/repository.py`:

```python
class DungeonRepository:
    def __init__(self, dungeons_dir: Path) -> None:
        """
        dungeons_dir must already exist. DungeonRepository does NOT create it.
        Call AppConfig.ensure_dirs() before constructing the repository.
        Pass None only when calling load_sample() — all other methods
        require a valid directory path.
        """
        ...

    def list_dungeons(self) -> list[str]:
        """Return stems of all .json dungeon files in dungeons_dir.
        Excludes _session.json files."""

    def load(self, name: str) -> Dungeon:
        """Load and validate dungeon by stem name. Raises FileNotFoundError."""

    def save(self, dungeon: Dungeon, name: str) -> None:
        """Serialise and write dungeon to <dungeons_dir>/<name>.json.
        Writes atomically: temp file then rename."""

    def load_session(self, name: str) -> SessionState | None:
        """Load session state if it exists, else return None."""

    def save_session(self, state: SessionState) -> None:
        """Write session state to <dungeons_dir>/<dungeon_id>_session.json."""

    def load_sample(self) -> Dungeon:
        """Load the bundled Tomb of the Forgotten King sample."""

    # --- Memory layer ---

    def load_room_memory(self, name: str, level_id: int) -> str:
        """Load the markdown memory for a level.
        Returns an empty string if no memory file exists yet.
        File path: <dungeons_dir>/<name>_memory/level_<level_id>.md"""

    def save_room_memory(self, name: str, level_id: int, content: str) -> None:
        """Overwrite the markdown memory for a level.
        Creates the <name>_memory/ directory if it does not exist.
        Writes atomically: temp file then rename."""

    def append_room_event(
        self,
        name: str,
        level_id: int,
        room_id: str,
        room_name: str,
        event: str,
    ) -> None:
        """Append a timestamped event line to a room's section in the level
        memory file. Creates the file and room section header if needed.

        Format appended:
            - <ISO date>: <event>

        If the room section (## Room <room_id> — <room_name>) does not exist
        in the file, it is created before the event line is appended.
        """
```

### Memory File Format

Memory files are plain markdown, stored at:
`<dungeons_dir>/<dungeon_stem>_memory/level_<N>.md`

```markdown
# Level 1 — The Sunken Vestibule: Play Memory

## Room 1-A — Flooded Entry
- 2026-04-23: Party entered cautiously. Rogue found a corroded iron key in the drain.
- 2026-04-23: Fighter triggered the pressure plate. Lost 4 HP.

## Room 1-C — Guard Post
- 2026-04-23: Party bypassed sleeping guards using Silence spell.
```

The file is human-readable and editable outside the app. The app treats it as
a UTF-8 text file — it reads the whole file for LLM context and overwrites it
on edit. No parsing of the markdown structure is required beyond appending to
the correct room section.
