# Dungeon Daddy — Campaign Migration Guide

## Back Up a Campaign

A campaign is a single folder under `<campaigns_dir>/<campaign_slug>/`. Copy the whole folder.

```bash
# Find the campaigns directory
# Default on Linux/Mac: ~/.local/share/DungeonDaddy/campaigns/
# Default on Windows:   %LOCALAPPDATA%\DungeonDaddy\campaigns\

# Example: back up "tomb_of_shadows"
cp -r ~/.local/share/DungeonDaddy/campaigns/tomb_of_shadows \
      ~/backups/tomb_of_shadows_2026-06-03
```

The backup contains:
- `campaign.duckdb` — all RPG state and narrative memory
- `rpg-memory/` — Markdown narrative memory files
- `dungeon.json` — dungeon design blueprint
- `session.json` — play session state
- `memory/`, `setting.md`, `party.md`, `level_N_design.md` — context docs

**Always back up before applying a migration or running repair tools.**

---

## Apply a Migration

Migrations are SQL files in `dungeon_daddy/data/migrations/`. They are applied automatically when the app starts or when any tool calls `repo.initialize_schema(migrations_dir)`.

To apply migrations manually (e.g., after adding a new migration file):

```python
from pathlib import Path
from dungeon_daddy.memory.repository import MemoryRepository

MIGRATIONS = Path("dungeon_daddy/data/migrations")
repo = MemoryRepository(Path("/path/to/campaign.duckdb"))
repo.initialize_schema(MIGRATIONS)
repo.close()
print("Migrations applied.")
```

Migrations are idempotent — already-applied migrations are skipped. The `schema_migration` table records which migrations have run.

**To check which migrations have been applied:**

```python
conn = repo._conn
rows = conn.execute("SELECT name, applied_at FROM schema_migration ORDER BY applied_at").fetchall()
for name, applied_at in rows:
    print(f"  {applied_at}  {name}")
```

---

## Export a Campaign to JSON

Use `export_campaign` to create a portable JSON bundle of all campaign state (actors, clocks, fallout, memory entries, scenes).

```bash
# Export to stdout
python tools/export_campaign.py \
  /path/to/campaign.duckdb \
  <campaign_id> \
  --out /path/to/backup.json
```

The `campaign_id` is the UUID stored in the `campaigns` table. If you don't know it:

```python
conn = repo._conn
rows = conn.execute("SELECT campaign_id, slug, title FROM campaigns").fetchall()
for row in rows:
    print(row)
```

The output JSON has these top-level keys:
```
campaign, actors, clocks, fallout, memory_entries, scenes
```

---

## Restore from an Export

Use `import_campaign_fixture` to load a JSON bundle into a (new or existing) DuckDB file.

```bash
python tools/import_campaign_fixture.py \
  /path/to/new_campaign.duckdb \
  /path/to/backup.json
```

After import, rebuild the search projection:

```bash
python tools/rebuild_memory_projection.py /path/to/new_campaign.duckdb
```

**Caution:** `import_campaign_fixture` uses `INSERT ... ON CONFLICT DO UPDATE`, so importing into an existing DB will overwrite matching IDs. Import into a fresh file when restoring to avoid conflicts.

---

## Full Round-Trip (Export → Import)

```bash
# 1. Back up the folder
cp -r campaigns/my_campaign /tmp/my_campaign_backup

# 2. Export state to JSON
python tools/export_campaign.py \
  campaigns/my_campaign/campaign.duckdb \
  <campaign_id> \
  --out /tmp/my_campaign_backup/bundle.json

# 3. Create a fresh DB and import
python tools/import_campaign_fixture.py \
  /tmp/restored/campaign.duckdb \
  /tmp/my_campaign_backup/bundle.json

# 4. Rebuild projection
python tools/rebuild_memory_projection.py /tmp/restored/campaign.duckdb

# 5. Validate
python tools/validate_campaign.py \
  /tmp/restored/campaign.duckdb \
  campaigns/my_campaign/rpg-memory/
```

A clean restore reports: `OK: no drift detected`.

---

## Adding a New Migration

1. Create a new SQL file: `dungeon_daddy/data/migrations/NNN_description.sql`  
   Use the next sequential number (e.g., `004_new_table.sql`).

2. Write idempotent SQL using `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` where supported.

3. Run the app or call `initialize_schema()` against a development campaign to verify the migration applies cleanly.

4. Add a test that seeds a fresh `MemoryRepository`, calls `initialize_schema`, and asserts the new schema is present.

5. Back up any production campaigns before shipping the migration.
