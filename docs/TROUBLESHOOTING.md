# Dungeon Daddy — Troubleshooting

## DB / Markdown Drift

**Symptom:** Memory entries exist in `campaign.duckdb` with no corresponding `.md` file, or `.md` files exist with no DB entry.

**Cause:** A crash during a write, a manual file move, or a failed migration.

**Fix:** Run the validator, then repair manually or rebuild.

```bash
# Report drift
python tools/validate_campaign.py <path/to/campaign.duckdb> <path/to/rpg-memory/>

# Example
python tools/validate_campaign.py \
  ~/.local/share/DungeonDaddy/campaigns/my_campaign/campaign.duckdb \
  ~/.local/share/DungeonDaddy/campaigns/my_campaign/rpg-memory/
```

If `missing_file` issues are reported, the DB has entries with no matching `.md`. Either restore the files from a backup or delete the orphaned DB entries.

If `orphan_markdown` issues are reported, `.md` files have no DB entry. Either re-import them or delete the orphaned files.

After manual repairs, rebuild the search projection:

```bash
python tools/rebuild_memory_projection.py <path/to/campaign.duckdb>
```

---

## Missing or Stale Migrations

**Symptom:** `OperationalError: Table 'X' does not exist` or missing columns.

**Cause:** A new migration was added but the DB was not updated (e.g., the campaign predates the migration).

**Fix:** Migrations are applied automatically by `MemoryRepository.initialize_schema()` on startup. If you are running a script directly, ensure you call:

```python
from pathlib import Path
from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS = Path("dungeon_daddy/data/migrations")
repo = MemoryRepository(Path("campaign.duckdb"))
repo.initialize_schema(MIGRATIONS)
```

The `schema_migration` table tracks which migrations have been applied. Already-applied migrations are skipped. Re-running `initialize_schema` is safe.

---

## Provider Key Not Set

**Symptom:** LLM calls fail with `AuthenticationError` or `missing OPENAI_API_KEY`.

**Fix:** Set the environment variable before launching the app.

```bash
# PowerShell
$env:OPENAI_API_KEY = "sk-..."
python -m dungeon_daddy

# bash
OPENAI_API_KEY=sk-... python -m dungeon_daddy
```

The active provider is OpenAI (`gpt-4o`). The `AnthropicProvider` is available but not wired as the default. To switch providers, change the provider passed to `DungeonMasterAgent` in `window.py`.

---

## Arcade Window Not Launching

**Symptom:** `python -m dungeon_daddy` exits immediately, shows a blank window, or crashes before the first frame.

**Common causes and fixes:**

### DPI scaling (Windows)
High-DPI monitors can cause the window to appear too small or blank. Run:

```bash
python tools/dpi.py
```

This reports the DPI settings detected by Arcade. If scaling is wrong, set `DPI_AWARENESS` in the Windows app manifest or run the app as `--dpi-unaware`.

### GPU / OpenGL driver
Arcade requires OpenGL 3.3+. Check your driver version:
- Update the GPU driver via Device Manager or the vendor's tool.
- On a VM or remote desktop, ensure GPU passthrough or a software OpenGL renderer (Mesa) is installed.

### Missing font assets
If font files are absent from `dungeon_daddy/assets/fonts/`, the app may crash in `load_fonts()`. Download the fonts from Google Fonts (Inter, JetBrains Mono, IM Fell English) and place them in that directory.

### Already-running instance
A previous window may have left a DuckDB lock. Check for orphaned `python` processes and kill them before relaunching.

```bash
# Stop a running Arcade window
python tools/arcade_stop.py
```

---

## Memory Search Returns No Results

**Symptom:** The MEM tab shows no entries even though memory entries exist in the DB.

**Cause:** The `memory_search_projection` cache table is empty or stale.

**Fix:**

```bash
python tools/rebuild_memory_projection.py <path/to/campaign.duckdb>
```

---

## Test Suite Failures After a New Migration

**Symptom:** Integration tests fail with schema errors after adding a migration.

**Fix:** Ensure the test fixture calls `repo.initialize_schema(MIGRATIONS)` against the shared migrations path. The `tests/fixtures/phase32_campaign.py` helper does this automatically. For new test files, import and call `seed_campaign(repo)` rather than constructing repos manually.
