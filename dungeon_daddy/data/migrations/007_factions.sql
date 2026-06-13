CREATE TABLE IF NOT EXISTS factions (
    faction_id   TEXT PRIMARY KEY,
    campaign_id  TEXT NOT NULL,
    slug         TEXT NOT NULL,
    display_name TEXT NOT NULL,
    concept      TEXT,
    goal         TEXT,
    status       TEXT NOT NULL DEFAULT 'active',
    reputation   TEXT NOT NULL DEFAULT 'neutral',
    tier         INTEGER NOT NULL DEFAULT 0,
    tags         TEXT NOT NULL DEFAULT '[]',
    UNIQUE(campaign_id, slug)
);
