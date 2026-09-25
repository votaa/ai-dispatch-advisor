import shutil
import sqlite3
from pathlib import Path

import pytest

from app.database_migrations import (
    MIGRATIONS_DIR,
    MigrationError,
    applied_migrations,
    run_migrations,
)


def test_fresh_database_applies_all_migrations(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "fresh.db") as connection:
        version = run_migrations(connection)
        history = applied_migrations(connection)
        audit_columns = _columns(connection, "recommendation_audit_events")
        assignment_columns = _columns(connection, "demo_assignments")
        mutation_columns = _columns(connection, "assignment_mutations")
        indexes = _indexes(connection)

    assert version == 6
    assert [(row["version"], row["name"]) for row in history] == [
        (1, "create_decision_store"),
        (2, "add_scenario_scope"),
        (3, "add_decision_indexes"),
        (4, "create_assignment_mutations"),
        (5, "add_assignment_reason_categories"),
        (6, "assignment_mutation_history"),
    ]
    assert "scenario_id" in audit_columns
    assert "scenario_id" in assignment_columns
    assert {"new_assignment_id", "new_crew_id", "resulting_incident_status"} <= mutation_columns
    assert "idx_recommendation_audit_events_scenario_incident" in indexes
    assert "idx_demo_assignments_scenario_active" in indexes
    assert "idx_assignment_mutations_scenario_created" in indexes


def test_migrations_are_idempotent_and_preserve_rows(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "idempotent.db") as connection:
        run_migrations(connection)
        connection.execute(
            """
            INSERT INTO recommendation_audit_events (
              event_id, scenario_id, recommendation_id, incident_id, crew_id,
              action, reason, actor, confidence, explanation_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event-1",
                "storm",
                "REC-1",
                "INC-1",
                "CR-1",
                "accepted",
                None,
                "tester",
                "high",
                "{}",
                "2026-08-13T12:00:00+00:00",
            ),
        )
        connection.commit()

        assert run_migrations(connection) == 6
        assert len(applied_migrations(connection)) == 6
        row = connection.execute(
            "SELECT scenario_id, recommendation_id FROM recommendation_audit_events"
        ).fetchone()

    assert row == ("storm", "REC-1")


def test_current_unversioned_schema_is_baselined_without_data_loss(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "current-unversioned.db") as connection:
        _create_current_unversioned_schema(connection)
        connection.execute(
            """
            INSERT INTO recommendation_audit_events (
              event_id, scenario_id, recommendation_id, incident_id, crew_id,
              action, reason, actor, confidence, explanation_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "existing-event",
                "crew-shortage",
                "REC-EXISTING",
                "INC-EXISTING",
                None,
                "deferred",
                "No qualified crew",
                "tester",
                "low",
                "{}",
                "2026-08-13T12:00:00+00:00",
            ),
        )
        connection.commit()

        run_migrations(connection)
        history = applied_migrations(connection)
        row = connection.execute(
            "SELECT scenario_id, reason FROM recommendation_audit_events WHERE event_id = ?",
            ("existing-event",),
        ).fetchone()

    assert [entry["version"] for entry in history] == [1, 2, 3, 4, 5, 6]
    assert row == ("crew-shortage", "No qualified crew")


def test_changed_applied_migration_is_rejected(tmp_path: Path) -> None:
    migration_copy = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, migration_copy)

    with sqlite3.connect(tmp_path / "checksum.db") as connection:
        run_migrations(connection, migration_copy)
        first_migration = migration_copy / "001_create_decision_store.sql"
        first_migration.write_text(
            first_migration.read_text(encoding="utf-8") + "\n-- changed\n",
            encoding="utf-8",
        )

        with pytest.raises(MigrationError, match="checksum"):
            run_migrations(connection, migration_copy)


def test_incomplete_existing_schema_is_rejected(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "incomplete.db") as connection:
        connection.execute("CREATE TABLE recommendation_audit_events (event_id TEXT PRIMARY KEY)")
        connection.commit()

        with pytest.raises(MigrationError, match="both decision tables are required"):
            run_migrations(connection)


def test_failed_migration_rolls_back_schema_and_history(tmp_path: Path) -> None:
    migration_copy = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, migration_copy)
    (migration_copy / "007_invalid_change.sql").write_text(
        """
        CREATE TABLE should_be_rolled_back (id TEXT PRIMARY KEY);
        INSERT INTO table_that_does_not_exist (id) VALUES ('fail');
        """,
        encoding="utf-8",
    )

    with sqlite3.connect(tmp_path / "rollback.db") as connection:
        with pytest.raises(MigrationError, match="007_invalid_change"):
            run_migrations(connection, migration_copy)

        assert "should_be_rolled_back" not in {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert [row["version"] for row in applied_migrations(connection)] == [1, 2, 3, 4, 5, 6]


def test_history_migration_recovers_replacement_without_inventing_outcome(tmp_path: Path) -> None:
    old_migrations = tmp_path / "old-migrations"
    old_migrations.mkdir()
    for source in sorted(MIGRATIONS_DIR.glob("0*.sql"))[:5]:
        shutil.copy(source, old_migrations / source.name)

    with sqlite3.connect(tmp_path / "upgrade.db") as connection:
        assert run_migrations(connection, old_migrations) == 5
        connection.execute(
            """
            INSERT INTO assignment_mutations (
              mutation_id, scenario_id, assignment_id, incident_id, crew_id,
              action, reason, actor, created_at, reason_category, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("MUT-OLD", "base", "ASG-OLD", "INC-1", "CR-OLD", "reassigned",
             "Crew unavailable", "tester", "2026-09-01T12:00:00+00:00",
             "crew_unavailable", None),
        )
        connection.execute(
            """
            INSERT INTO demo_assignments (
              assignment_id, scenario_id, incident_id, crew_id, status,
              assigned_at, notes, decision_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("ASG-NEW", "base", "INC-1", "CR-NEW", "active",
             "2026-09-01T12:00:00+00:00", "Reassigned", "MUT-OLD"),
        )
        connection.commit()

        assert run_migrations(connection) == 6
        row = connection.execute(
            """
            SELECT new_assignment_id, new_crew_id, resulting_incident_status
            FROM assignment_mutations WHERE mutation_id = 'MUT-OLD'
            """
        ).fetchone()

    assert row == ("ASG-NEW", "CR-NEW", None)


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _indexes(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _create_current_unversioned_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE recommendation_audit_events (
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

        CREATE TABLE demo_assignments (
          assignment_id TEXT PRIMARY KEY,
          scenario_id TEXT NOT NULL,
          incident_id TEXT NOT NULL,
          crew_id TEXT NOT NULL,
          status TEXT NOT NULL,
          assigned_at TEXT NOT NULL,
          notes TEXT NOT NULL,
          decision_event_id TEXT NOT NULL
        );
        """
    )
