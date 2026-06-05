# `tools/seed_rpg_state.py` Requirements

## Purpose

Patch existing campaign folders with RPG-ready data so Play Mode can test player-controlled actions, context bundles, world reactions, and memory retrieval.

## Required CLI

Suggested options:

```bash
python tools/seed_rpg_state.py --campaign <slug> --dry-run
python tools/seed_rpg_state.py --campaign <slug>
python tools/seed_rpg_state.py --all-existing-campaigns --dry-run
python tools/seed_rpg_state.py --all-existing-campaigns
python tools/seed_rpg_state.py --campaign <slug> --seed-pack seed_data/campaigns/<slug>/rpg_seed.json
```

## Required behavior

- Safe by default.
- Dry-run prints intended changes without writing.
- Idempotent: no duplicate records on repeated runs.
- Stable IDs based on campaign slug + semantic slug where possible.
- Uses current campaign folder layout.
- Creates missing DuckDB rows through repository/service methods where available.
- Does not destructively rewrite `dungeon.json`, `setting.md`, `party.md`, or level design docs.
- Writes a clear summary:

```text
Created:
Updated:
Skipped:
Warnings:
```

## Required seed entities

For each campaign:

```text
- campaign row
- session row
- active scene
- player-controlled actor(s)
- action ratings
- stress tracks
- dungeon-controlled NPC/monster/dungeon presence actors
- clocks
- memory entries
- memory tags
- optional room threat hooks
```

## Idempotency keys

Use stable keys such as:

```text
actor:<campaign_slug>:<actor_slug>
clock:<campaign_slug>:<clock_slug>
memory:<campaign_slug>:<memory_slug>
scene:<campaign_slug>:<location_slug>
```

## Validation

Seeder should warn if:

- campaign folder is missing
- campaign has no `dungeon.json`
- campaign has no `campaign.duckdb`
- campaign has no player-controlled actors after seed
- campaign has no active clocks after seed
- memory tags are not namespaced
- seed pack references unknown locations

## Test requirements

- dry-run creates no files/rows
- first apply creates expected records
- second apply creates zero duplicates
- missing campaign fails gracefully
- invalid seed pack returns clear error
