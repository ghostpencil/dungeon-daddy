ALTER TABLE object_transitions ADD COLUMN IF NOT EXISTS contested BOOLEAN DEFAULT false;
ALTER TABLE object_transitions ADD COLUMN IF NOT EXISTS action_verb TEXT;
