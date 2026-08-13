from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
MIGRATION_FILENAME = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")

AUDIT_V1_COLUMNS = {
    "event_id",
    "recommendation_id",
    "incident_id",
    "crew_id",
    "action",
    "reason",
    "actor",
    "confidence",
    "explanation_json",
    "created_at",
}
ASSIGNMENT_V1_COLUMNS = {
    "assignment_id",
    "incident_id",
    "crew_id",
    "status",
    "assigned_at",
    "notes",
    "decision_event_id",
}


class MigrationError(RuntimeError):
    """Raised when migration history or an existing database is unsafe to upgrade."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str
    sql: str


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    if not directory.is_dir():
        raise MigrationError(f"Migration directory not found: {directory}")

    migrations: list[Migration] = []
    for path in sorted(directory.iterdir()):
        if path.name.startswith("."):
            continue
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {path.name}")
        payload = path.read_bytes()
        migrations.append(
            Migration(
                version=int(match.group("version")),
                name=match.group("name"),
                checksum=hashlib.sha256(payload).hexdigest(),
                sql=payload.decode("utf-8"),
            )
        )

    if not migrations:
        raise MigrationError(f"No migrations found in: {directory}")
    versions = [migration.version for migration in migrations]
    expected_versions = list(range(1, len(migrations) + 1))
    if versions != expected_versions:
        raise MigrationError(
            f"Migration versions must be consecutive from 001; found {versions}"
        )
    return migrations


def run_migrations(
    connection: sqlite3.Connection,
    directory: Path = MIGRATIONS_DIR,
) -> int:
    migrations = discover_migrations(directory)
    _ensure_history_table(connection)
    _baseline_unversioned_database(connection, migrations)
    applied = _validated_history(connection, migrations)

    for migration in migrations:
        if migration.version not in applied:
            _apply_migration(connection, migration)

    return migrations[-1].version


def applied_migrations(connection: sqlite3.Connection) -> list[dict[str, object]]:
    if "schema_migrations" not in _table_names(connection):
        return []
    rows = connection.execute(
        """
        SELECT version, name, checksum, applied_at
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()
    return [
        {
            "version": row[0],
            "name": row[1],
            "checksum": row[2],
            "applied_at": row[3],
        }
        for row in rows
    ]


def _ensure_history_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          checksum TEXT NOT NULL,
          applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _baseline_unversioned_database(
    connection: sqlite3.Connection,
    migrations: list[Migration],
) -> None:
    if connection.execute("SELECT 1 FROM schema_migrations LIMIT 1").fetchone():
        return

    tables = _table_names(connection)
    has_audit = "recommendation_audit_events" in tables
    has_assignments = "demo_assignments" in tables
    if not has_audit and not has_assignments:
        return
    if has_audit != has_assignments:
        raise MigrationError(
            "Existing decision database is incomplete; both decision tables are required"
        )

    audit_columns = _table_columns(connection, "recommendation_audit_events")
    assignment_columns = _table_columns(connection, "demo_assignments")
    if not AUDIT_V1_COLUMNS.issubset(audit_columns) or not ASSIGNMENT_V1_COLUMNS.issubset(
        assignment_columns
    ):
        raise MigrationError("Existing decision database does not match a supported legacy schema")

    audit_is_scoped = "scenario_id" in audit_columns
    assignments_are_scoped = "scenario_id" in assignment_columns
    if audit_is_scoped != assignments_are_scoped:
        raise MigrationError("Existing decision database has inconsistent scenario scoping")

    baseline_version = 2 if audit_is_scoped else 1
    if baseline_version > migrations[-1].version:
        raise MigrationError("Existing decision database is newer than available migrations")

    applied_at = datetime.now(timezone.utc).isoformat()
    try:
        connection.execute("BEGIN IMMEDIATE")
        for migration in migrations[:baseline_version]:
            connection.execute(
                """
                INSERT INTO schema_migrations (version, name, checksum, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (migration.version, migration.name, migration.checksum, applied_at),
            )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise MigrationError("Failed to baseline existing decision database") from exc


def _validated_history(
    connection: sqlite3.Connection,
    migrations: list[Migration],
) -> set[int]:
    history = applied_migrations(connection)
    if not history:
        return set()

    available = {migration.version: migration for migration in migrations}
    versions = [int(row["version"]) for row in history]
    if versions != list(range(1, max(versions) + 1)):
        raise MigrationError(f"Applied migration history is not consecutive: {versions}")

    for row in history:
        version = int(row["version"])
        migration = available.get(version)
        if migration is None:
            raise MigrationError(
                f"Database migration {version:03d} is newer than this application"
            )
        if row["name"] != migration.name:
            raise MigrationError(f"Migration {version:03d} name does not match its history")
        if row["checksum"] != migration.checksum:
            raise MigrationError(f"Migration {version:03d} checksum does not match its history")
    return set(versions)


def _apply_migration(connection: sqlite3.Connection, migration: Migration) -> None:
    try:
        connection.execute("BEGIN IMMEDIATE")
        for statement in _sql_statements(migration.sql):
            connection.execute(statement)
        connection.execute(
            """
            INSERT INTO schema_migrations (version, name, checksum, applied_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                migration.version,
                migration.name,
                migration.checksum,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
    except (sqlite3.Error, MigrationError) as exc:
        connection.rollback()
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(
            f"Failed to apply migration {migration.version:03d}_{migration.name}"
        ) from exc


def _sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        raise MigrationError("Migration contains an incomplete SQL statement")
    return statements


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
