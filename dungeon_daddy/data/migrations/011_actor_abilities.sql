CREATE TABLE IF NOT EXISTS actor_abilities (
    actor_id        TEXT NOT NULL,
    ability_slug    TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    description     TEXT NOT NULL,
    source          TEXT NOT NULL,
    surfaces_as_verb BOOLEAN NOT NULL DEFAULT FALSE,
    target_types    TEXT NOT NULL DEFAULT '[]',
    cost_type       TEXT NOT NULL DEFAULT 'none',
    cost_amount     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (actor_id, ability_slug)
);
ALTER TABLE actors ADD COLUMN playbook_slug TEXT;
ALTER TABLE actors ADD COLUMN tags TEXT DEFAULT '[]'
