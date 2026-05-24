# Tech Stack

## Runtime

| Requirement | Value |
|---|---|
| Python version | 3.12 or higher |
| Target OS | Windows 10 / Windows 11 (64-bit) |
| Window model | Single Arcade window, no external GUI framework |

---

## Approved Libraries

### `arcade >= 3.0`

**Role:** Game engine, window management, rendering, and UI panels.

Arcade owns the main window and the game loop. All rendering — the dungeon map, the
panel backgrounds, the chrome decorations — is done through Arcade's drawing primitives
and its `UIManager` system.

Key Arcade subsystems used:
- `arcade.Window` — application window
- `arcade.View` — swappable views for Design Mode and Play Mode
- `arcade.gui.UIManager` — UI widget tree per view
- `arcade.gui.UIBoxLayout`, `UIAnchorLayout` — panel layout
- `arcade.gui.UILabel`, `UIInputText`, `UITextArea` — text widgets
- `arcade.gui.UIScrollArea` — scrollable chat history
- `arcade.gui.UIFlatButton` — interactive buttons
- `arcade.draw_*` primitives — map rendering and custom chrome

Arcade 3.x requires Python 3.9+. Version 3.12 is fully supported.

---

### `anthropic >= 0.40`

**Role:** LLM SDK. Used exclusively through the `LLMProvider` protocol defined in
`spec/LLM_INTERFACE.md`. Application code never imports `anthropic` directly — only
`dungeon_daddy/llm/anthropic_provider.py` imports it.

Use the **synchronous** client (`anthropic.Anthropic`). Background threading (Python
stdlib `threading`) handles non-blocking calls. Do not use the async client.

---

### `pydantic >= 2.9`

**Role:** Data models, validation, and JSON serialization.

All domain objects (Dungeon, Level, Room, Connection, Loop, etc.) are Pydantic
`BaseModel` subclasses. Serialization to/from JSON uses `.model_dump(mode="json")`
and `.model_validate(data)`. This guarantees that saved files are always valid and
that invalid data is caught at the boundary.

---

### `pytest >= 8.3`

**Role:** Test framework. All tests (unit and integration) use pytest. Tests are
written before application code — see `spec/TESTING.md`.

---

### `pytest-mock >= 3.14`

**Role:** Provides the `mocker` fixture for clean mocking of LLM provider calls and
file I/O in unit tests. Ensures unit tests never make real network calls or write
to disk.

---

### `platformdirs >= 4.2`

**Role:** Cross-platform user data directory resolution. Returns a `pathlib.Path`
pointing to the correct OS-specific location for application data:
- Windows: `%APPDATA%\DungeonDaddy` (e.g. `C:\Users\<name>\AppData\Roaming\DungeonDaddy`)
- macOS: `~/Library/Application Support/DungeonDaddy`
- Linux: `~/.local/share/DungeonDaddy`

Usage in `config.py`:
```python
from platformdirs import user_data_path
user_data_dir: Path = user_data_path("DungeonDaddy", appauthor=False)
```

`platformdirs` 4.x requires Python 3.8+. Version 3.12 is fully supported.

---

## Explicitly Excluded

The following are **not** approved and must not be added without user confirmation:

- Any async framework (`asyncio`, `anyio`, `trio`)
- Any second GUI framework (`tkinter`, `PyQt`, `Dear PyGui`, `wx`)
- Any ORM or database (`sqlite3` wrappers, `SQLAlchemy`, etc.)
- Any HTTP client library (`httpx`, `requests`) — the Anthropic SDK handles networking
- Any testing extras beyond `pytest` and `pytest-mock`

---

## Dependency File

The project must include a `requirements.txt` (runtime) and `requirements-dev.txt`
(test tooling). Pin to minimum versions, not exact versions, so the implementing
environment can resolve the latest compatible releases.

**`requirements.txt`**
```
arcade>=3.0
anthropic>=0.40
pydantic>=2.9
platformdirs>=4.2
```

**`requirements-dev.txt`**
```
-r requirements.txt
pytest>=8.3
pytest-mock>=3.14
```

---

## Asset Bundling

### Font Files

The app requires 8 TTF font files. They are **not** downloaded at runtime —
they must be committed to the repository under `dungeon_daddy/assets/fonts/`.

Download sources (Google Fonts, free/open license):

| File | Google Fonts URL |
|---|---|
| `IMFellEnglish-Regular.ttf` | fonts.google.com/specimen/IM+Fell+English |
| `IMFellEnglish-Italic.ttf` | fonts.google.com/specimen/IM+Fell+English |
| `IMFellEnglishSC-Regular.ttf` | fonts.google.com/specimen/IM+Fell+English+SC |
| `JetBrainsMono-Regular.ttf` | fonts.google.com/specimen/JetBrains+Mono |
| `JetBrainsMono-Medium.ttf` | fonts.google.com/specimen/JetBrains+Mono |
| `Inter-Regular.ttf` | fonts.google.com/specimen/Inter |
| `Inter-Medium.ttf` | fonts.google.com/specimen/Inter |
| `Inter-Bold.ttf` | fonts.google.com/specimen/Inter |

### Bundled Data Files

These JSON files are part of the package and loaded via `importlib.resources`:

| File | Purpose |
|---|---|
| `dungeon_daddy/data/loop_patterns.json` | Built-in loop pattern catalog |
| `dungeon_daddy/data/samples/tomb_of_the_forgotten_king.json` | Sample dungeon |

### Distribution

The application is distributed as a **source package** — users run it with:
```
pip install -r requirements.txt
python -m dungeon_daddy
```

No PyInstaller, no wheel packaging, no installer — source-only for now.
`dungeon_daddy/assets/` and `dungeon_daddy/data/` must be included in the
package via `MANIFEST.in` or `pyproject.toml` `[tool.setuptools.package-data]`
if packaging is added later.
