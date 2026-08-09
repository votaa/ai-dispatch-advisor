CREATE TABLE IF NOT EXISTS incidents (
  incident_id TEXT PRIMARY KEY,
  region TEXT NOT NULL,
  municipality TEXT NOT NULL,
  feeder TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  customers_out INTEGER NOT NULL,
  critical_facility INTEGER NOT NULL,
  hazard TEXT NOT NULL,
  required_skill TEXT NOT NULL,
  age_minutes INTEGER NOT NULL,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  etr TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crews (
  crew_id TEXT PRIMARY KEY,
  crew_name TEXT NOT NULL,
  home_region TEXT NOT NULL,
  status TEXT NOT NULL,
  capability TEXT NOT NULL,
  current_location TEXT NOT NULL,
  shift_remaining_hours REAL NOT NULL,
  storm_ready INTEGER NOT NULL,
  travel_minutes_to_selected_incident INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
  assignment_id TEXT PRIMARY KEY,
  incident_id TEXT NOT NULL,
  crew_id TEXT NOT NULL,
  status TEXT NOT NULL,
  assigned_at TEXT NOT NULL,
  notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendation_audit_events (
  event_id TEXT PRIMARY KEY,
  scenario_id TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS demo_assignments (
  assignment_id TEXT PRIMARY KEY,
  scenario_id TEXT NOT NULL,
  incident_id TEXT NOT NULL,
  crew_id TEXT NOT NULL,
  status TEXT NOT NULL,
  assigned_at TEXT NOT NULL,
  notes TEXT NOT NULL,
  decision_event_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recommendation_audit_events_scenario_incident
  ON recommendation_audit_events (scenario_id, incident_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_assignments_scenario_active
  ON demo_assignments (scenario_id, crew_id, status);
