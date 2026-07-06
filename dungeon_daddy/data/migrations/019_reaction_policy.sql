ALTER TABLE room_objects ADD COLUMN IF NOT EXISTS reaction_policy TEXT DEFAULT 'ambient';

CREATE TABLE IF NOT EXISTS object_reaction_bindings (
    binding_id    TEXT PRIMARY KEY,
    object_id     TEXT NOT NULL,
    action_verb   TEXT NOT NULL,
    outcome       TEXT NOT NULL,
    clock_slug    TEXT,
    clock_delta   INTEGER NOT NULL DEFAULT 0,
    stress_track  TEXT,
    stress_amount INTEGER NOT NULL DEFAULT 0
);
