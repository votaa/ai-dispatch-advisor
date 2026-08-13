CREATE TABLE recommendation_audit_events (
  event_id TEXT PRIMARY KEY,
  recommendation_id TEXT NOT NULL,
  incident_id TEXT NOT NULL,
  crew_id TEXT,
  action TEXT NOT NULL,
  reason TEXT,
  actor TEXT NOT NULL,
  confidence TEXT,
  explanation_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE demo_assignments (
  assignment_id TEXT PRIMARY KEY,
  incident_id TEXT NOT NULL,
  crew_id TEXT NOT NULL,
  status TEXT NOT NULL,
  assigned_at TEXT NOT NULL,
  notes TEXT NOT NULL,
  decision_event_id TEXT NOT NULL
);
