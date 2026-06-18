ALTER TABLE items ADD COLUMN IF NOT EXISTS room_id TEXT;

CREATE TABLE IF NOT EXISTS room_objects (
    object_id    TEXT PRIMARY KEY,
    campaign_id  TEXT NOT NULL,
    room_id      TEXT NOT NULL,
    level_id     TEXT NOT NULL,
    slug         TEXT NOT NULL,
    display_name TEXT NOT NULL,
    archetype    TEXT NOT NULL,
    description  TEXT NOT NULL,
    current_state TEXT NOT NULL,
    UNIQUE(campaign_id, slug)
);

CREATE TABLE IF NOT EXISTS object_transitions (
    transition_id       TEXT PRIMARY KEY,
    object_id           TEXT NOT NULL,
    from_state          TEXT NOT NULL,
    to_state            TEXT NOT NULL,
    trigger             TEXT NOT NULL,
    requires_item_slug  TEXT,
    spawns_item_slug    TEXT,
    advances_clock_slug TEXT
);
