ALTER TABLE assignment_mutations
  ADD COLUMN new_assignment_id TEXT;

ALTER TABLE assignment_mutations
  ADD COLUMN new_crew_id TEXT;

ALTER TABLE assignment_mutations
  ADD COLUMN resulting_incident_status TEXT;

-- Earlier reassignment rows can recover their replacement from the linked
-- assignment. Historical incident status was never recorded, so leave it null.
UPDATE assignment_mutations
SET new_assignment_id = (
  SELECT assignment_id FROM demo_assignments
  WHERE decision_event_id = assignment_mutations.mutation_id
    AND scenario_id = assignment_mutations.scenario_id
)
WHERE action = 'reassigned';

UPDATE assignment_mutations
SET new_crew_id = (
  SELECT crew_id FROM demo_assignments
  WHERE decision_event_id = assignment_mutations.mutation_id
    AND scenario_id = assignment_mutations.scenario_id
)
WHERE action = 'reassigned';

CREATE INDEX idx_assignment_mutations_scenario_created
  ON assignment_mutations (scenario_id, created_at DESC, mutation_id DESC);
