import json
import sqlite3

from app import decision_store
from app.database_migrations import applied_migrations


def test_init_store_migrates_existing_rows_to_base_scenario() -> None:
    with sqlite3.connect(decision_store.DB_PATH) as connection:
        connection.executescript(
            """
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
            """
        )
        connection.execute(
            """
            INSERT INTO recommendation_audit_events (
              event_id, recommendation_id, incident_id, crew_id, action, reason,
              actor, confidence, explanation_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event-before-migration",
                "REC-INC-1001-CR-01",
                "INC-1001",
                "CR-01",
                "accepted",
                None,
                "demo-dispatcher",
                "high",
                json.dumps({"recommendation_id": "REC-INC-1001-CR-01"}),
                "2026-08-09T12:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO demo_assignments (
              assignment_id, incident_id, crew_id, status, assigned_at, notes, decision_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "assignment-before-migration",
                "INC-1001",
                "CR-01",
                "active",
                "2026-08-09T12:00:00+00:00",
                "Existing assignment",
                "event-before-migration",
            ),
        )

    decision_store.init_store()

    with sqlite3.connect(decision_store.DB_PATH) as connection:
        audit_columns = {row[1] for row in connection.execute("PRAGMA table_info(recommendation_audit_events)")}
        assignment_columns = {row[1] for row in connection.execute("PRAGMA table_info(demo_assignments)")}
        audit_scenario = connection.execute(
            "SELECT scenario_id FROM recommendation_audit_events WHERE event_id = ?",
            ("event-before-migration",),
        ).fetchone()[0]
        assignment_scenario = connection.execute(
            "SELECT scenario_id FROM demo_assignments WHERE assignment_id = ?",
            ("assignment-before-migration",),
        ).fetchone()[0]
        migration_versions = [row["version"] for row in applied_migrations(connection)]
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
            )
        }

    assert "scenario_id" in audit_columns
    assert "scenario_id" in assignment_columns
    assert audit_scenario == "base"
    assert assignment_scenario == "base"
    assert migration_versions == [1, 2, 3]
    assert "idx_recommendation_audit_events_scenario_incident" in indexes
    assert "idx_demo_assignments_scenario_active" in indexes
    assert decision_store.recent_decisions("storm") == []
    assert decision_store.recent_decisions("base")[0]["event_id"] == "event-before-migration"
