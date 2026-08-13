ALTER TABLE recommendation_audit_events
  ADD COLUMN scenario_id TEXT NOT NULL DEFAULT 'base';

ALTER TABLE demo_assignments
  ADD COLUMN scenario_id TEXT NOT NULL DEFAULT 'base';
