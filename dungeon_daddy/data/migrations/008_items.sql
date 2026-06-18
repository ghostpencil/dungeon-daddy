CREATE TABLE IF NOT EXISTS items (
    item_id         TEXT PRIMARY KEY,
    campaign_id     TEXT NOT NULL,
    slug            TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    item_type       TEXT NOT NULL,
    description     TEXT NOT NULL,
    owner_actor_id  TEXT,
    level_id        TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    charges_current INTEGER,
    charges_max     INTEGER,
    is_equipped     BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(campaign_id, slug)
);

CREATE TABLE IF NOT EXISTS item_features (
    feature_id   TEXT PRIMARY KEY,
    item_id      TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    action_key   TEXT NOT NULL,
    modifier     INTEGER
);
