CREATE TABLE IF NOT EXISTS room_exits (
    exit_id                  TEXT PRIMARY KEY,
    campaign_id              TEXT NOT NULL,
    from_room_id             TEXT NOT NULL,
    to_room_id               TEXT NOT NULL,
    level_id                 TEXT NOT NULL,
    label                    TEXT NOT NULL,
    exit_type                TEXT NOT NULL,
    connector_type           TEXT,
    to_level_id              TEXT,
    status                   TEXT NOT NULL,
    requires_item_slug       TEXT,
    requires_object_id       TEXT,
    requires_object_state    TEXT,
    requires_clock_slug      TEXT,
    requires_clock_min_filled INTEGER,
    requires_memory_slug     TEXT
);
