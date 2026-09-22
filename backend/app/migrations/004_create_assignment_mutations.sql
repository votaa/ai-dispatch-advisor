CREATE TABLE assignment_mutations (
  mutation_id TEXT PRIMARY KEY,
  scenario_id TEXT NOT NULL,
  assignment_id TEXT NOT NULL,
  incident_id TEXT NOT NULL,
  crew_id TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_assignment_mutations_scenario_assignment
  ON assignment_mutations (scenario_id, assignment_id, created_at);
