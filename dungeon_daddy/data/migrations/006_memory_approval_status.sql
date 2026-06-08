UPDATE memory_entries SET status = 'approved' WHERE status = 'active';
UPDATE memory_entries SET status = 'archived' WHERE status = 'resolved';
