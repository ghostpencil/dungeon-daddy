-- RPG and memory foundation schema for Dungeon Daddy

CREATE TABLE IF NOT EXISTS schema_migration (
    name TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    slug        TEXT NOT NULL,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id     TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    played_at      TIMESTAMP,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS scenes (
    scene_id       TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL,
    session_id     TEXT,
    location_slug  TEXT,
    status         TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS actors (
    actor_id     TEXT PRIMARY KEY,
    campaign_id  TEXT NOT NULL,
    actor_type   TEXT NOT NULL,
    slug         TEXT NOT NULL,
    display_name TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS action_ratings (
    actor_id   TEXT NOT NULL,
    action_key TEXT NOT NULL,
    rating     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (actor_id, action_key)
);

CREATE TABLE IF NOT EXISTS stress_tracks (
    actor_id  TEXT NOT NULL,
    track_key TEXT NOT NULL,
    capacity  INTEGER NOT NULL DEFAULT 6,
    filled    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (actor_id, track_key)
);

CREATE TABLE IF NOT EXISTS abilities (
    actor_id    TEXT NOT NULL,
    ability_key TEXT NOT NULL,
    value       TEXT,
    PRIMARY KEY (actor_id, ability_key)
);

CREATE TABLE IF NOT EXISTS clocks (
    clock_id    TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    label       TEXT NOT NULL,
    segments    INTEGER NOT NULL,
    filled      INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS action_resolutions (
    resolution_id TEXT PRIMARY KEY,
    campaign_id   TEXT NOT NULL,
    scene_id      TEXT,
    actor_id      TEXT NOT NULL,
    action_key    TEXT NOT NULL,
    outcome       TEXT NOT NULL,
    resolved_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fallout (
    fallout_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    actor_id    TEXT NOT NULL,
    track_key   TEXT NOT NULL,
    severity    TEXT NOT NULL,
    title       TEXT NOT NULL,
    summary     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS memory_entries (
    memory_id     TEXT PRIMARY KEY,
    campaign_id   TEXT NOT NULL,
    type          TEXT NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'active',
    importance    INTEGER NOT NULL DEFAULT 5,
    markdown_path TEXT,
    checksum      TEXT
);

CREATE TABLE IF NOT EXISTS memory_tags (
    memory_id TEXT NOT NULL,
    tag       TEXT NOT NULL,
    PRIMARY KEY (memory_id, tag)
);

CREATE TABLE IF NOT EXISTS memory_links (
    from_id   TEXT NOT NULL,
    to_id     TEXT NOT NULL,
    link_type TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id, link_type)
);

CREATE TABLE IF NOT EXISTS domain_events (
    event_id    TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
