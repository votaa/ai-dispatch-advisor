CREATE INDEX IF NOT EXISTS idx_recommendation_audit_events_scenario_incident
  ON recommendation_audit_events (scenario_id, incident_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_assignments_scenario_active
  ON demo_assignments (scenario_id, crew_id, status);
