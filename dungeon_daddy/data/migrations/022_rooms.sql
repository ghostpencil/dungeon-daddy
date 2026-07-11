CREATE TABLE IF NOT EXISTS rooms (
    room_id       TEXT NOT NULL,
    campaign_id   TEXT NOT NULL,
    level_id      TEXT NOT NULL,
    slug          TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    room_type     TEXT NOT NULL,
    summary       TEXT DEFAULT '',
    quest_role    TEXT,
    markdown_path TEXT,
    checksum      TEXT,
    tags          TEXT DEFAULT '[]',
    PRIMARY KEY (campaign_id, room_id)
);
