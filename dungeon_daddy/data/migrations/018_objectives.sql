CREATE TABLE IF NOT EXISTS objectives (
    objective_id              TEXT PRIMARY KEY,
    campaign_id               TEXT NOT NULL,
    slug                      TEXT NOT NULL,
    title                     TEXT NOT NULL,
    description               TEXT NOT NULL,
    tier_index                INTEGER NOT NULL,
    status                    TEXT NOT NULL,
    completion_kind           TEXT NOT NULL,
    completion_target_slug    TEXT NOT NULL,
    completion_required_state TEXT,
    advances_clock_slug       TEXT,
    UNIQUE(campaign_id, slug)
);

CREATE TABLE IF NOT EXISTS objective_knowledge (
    objective_id TEXT NOT NULL,
    ordinal      INTEGER NOT NULL,
    secret       TEXT NOT NULL
);
