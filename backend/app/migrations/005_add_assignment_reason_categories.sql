ALTER TABLE assignment_mutations
  ADD COLUMN reason_category TEXT NOT NULL DEFAULT 'other';

ALTER TABLE assignment_mutations
  ADD COLUMN note TEXT;
