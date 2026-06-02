-- Dungeon Daddy RPG + Memory Foundation
-- Migration: 001_rpg_memory_foundation

CREATE TABLE IF NOT EXISTS schema_migration (
    migration_id VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    checksum VARCHAR
);

CREATE TABLE IF NOT EXISTS campaign (
    campaign_id VARCHAR PRIMARY KEY,
    slug VARCHAR NOT NULL UNIQUE,
    title VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS session (
    session_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    session_number INTEGER NOT NULL,
    title VARCHAR,
    started_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    ended_at TIMESTAMP,
    recap_memory_id VARCHAR
);

CREATE TABLE IF NOT EXISTS scene (
    scene_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    session_id VARCHAR REFERENCES session(session_id),
    location_ref VARCHAR,
    title VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active',
    summary VARCHAR,
    started_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    ended_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actor (
    actor_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    actor_type VARCHAR NOT NULL,
    slug VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    concept VARCHAR,
    disposition VARCHAR,
    markdown_path VARCHAR,
    markdown_sha256 VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    UNIQUE(campaign_id, slug)
);

CREATE TABLE IF NOT EXISTS actor_action (
    actor_id VARCHAR NOT NULL REFERENCES actor(actor_id),
    action_key VARCHAR NOT NULL,
    rating SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (actor_id, action_key)
);

CREATE TABLE IF NOT EXISTS actor_track (
    actor_id VARCHAR NOT NULL REFERENCES actor(actor_id),
    track_key VARCHAR NOT NULL,
    current_value SMALLINT NOT NULL DEFAULT 0,
    max_value SMALLINT NOT NULL,
    PRIMARY KEY (actor_id, track_key)
);

CREATE TABLE IF NOT EXISTS ability (
    ability_id VARCHAR PRIMARY KEY,
    rules_key VARCHAR NOT NULL UNIQUE,
    display_name VARCHAR NOT NULL,
    body_markdown TEXT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS actor_ability (
    actor_id VARCHAR NOT NULL REFERENCES actor(actor_id),
    ability_id VARCHAR NOT NULL REFERENCES ability(ability_id),
    acquired_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (actor_id, ability_id)
);

CREATE TABLE IF NOT EXISTS clock (
    clock_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    scene_id VARCHAR REFERENCES scene(scene_id),
    owner_ref VARCHAR,
    clock_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    segments_total SMALLINT NOT NULL,
    segments_filled SMALLINT NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'active',
    metadata JSON
);

CREATE TABLE IF NOT EXISTS action_resolution (
    action_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    session_id VARCHAR REFERENCES session(session_id),
    scene_id VARCHAR REFERENCES scene(scene_id),
    actor_id VARCHAR NOT NULL REFERENCES actor(actor_id),
    action_key VARCHAR NOT NULL,
    goal TEXT NOT NULL,
    risk_level VARCHAR NOT NULL,
    effect_level VARCHAR NOT NULL,
    dice_json JSON NOT NULL,
    highest_die SMALLINT NOT NULL,
    outcome VARCHAR NOT NULL,
    momentum_delta SMALLINT NOT NULL DEFAULT 0,
    consequence_json JSON,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS fallout (
    fallout_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    actor_id VARCHAR NOT NULL REFERENCES actor(actor_id),
    source_action_id VARCHAR REFERENCES action_resolution(action_id),
    track_key VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    mechanical_hooks JSON,
    summary TEXT NOT NULL,
    markdown_path VARCHAR,
    markdown_sha256 VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_entry (
    memory_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR NOT NULL REFERENCES campaign(campaign_id),
    memory_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    body_text TEXT,
    markdown_path VARCHAR NOT NULL,
    markdown_sha256 VARCHAR,
    importance DOUBLE NOT NULL DEFAULT 0.5,
    status VARCHAR NOT NULL DEFAULT 'active',
    source_scene_id VARCHAR REFERENCES scene(scene_id),
    source_session_id VARCHAR REFERENCES session(session_id),
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS tag (
    tag_id VARCHAR PRIMARY KEY,
    namespace VARCHAR NOT NULL,
    slug VARCHAR NOT NULL UNIQUE,
    label VARCHAR NOT NULL,
    parent_tag_id VARCHAR REFERENCES tag(tag_id)
);

CREATE TABLE IF NOT EXISTS memory_tag (
    memory_id VARCHAR NOT NULL REFERENCES memory_entry(memory_id),
    tag_id VARCHAR NOT NULL REFERENCES tag(tag_id),
    weight SMALLINT NOT NULL DEFAULT 1,
    PRIMARY KEY (memory_id, tag_id)
);

CREATE TABLE IF NOT EXISTS memory_link (
    memory_id VARCHAR NOT NULL REFERENCES memory_entry(memory_id),
    link_type VARCHAR NOT NULL,
    target_id VARCHAR NOT NULL,
    relation VARCHAR NOT NULL,
    PRIMARY KEY (memory_id, link_type, target_id, relation)
);

CREATE TABLE IF NOT EXISTS domain_event (
    event_id VARCHAR PRIMARY KEY,
    campaign_id VARCHAR REFERENCES campaign(campaign_id),
    aggregate_type VARCHAR NOT NULL,
    aggregate_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    causation_id VARCHAR,
    correlation_id VARCHAR,
    payload JSON NOT NULL,
    occurred_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);
