-- Dungeon Daddy Memory Full-Text Search Projection
-- Migration: 002_memory_fts
-- Apply only after basic memory persistence works.

INSTALL fts;
LOAD fts;

-- Recreate the index when memory_entry body_text/title/summary changes.
-- DuckDB FTS indexes are not an automatic replacement for sync logic.

PRAGMA create_fts_index(
    'memory_entry',
    'memory_id',
    'title',
    'summary',
    'body_text',
    stemmer = 'porter',
    stopwords = 'english',
    ignore = '(\\.|[^a-z])+',
    strip_accents = 1,
    lower = 1,
    overwrite = 1
);
