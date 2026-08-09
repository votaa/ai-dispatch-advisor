from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4


ActionStatus = Literal["accepted", "modified", "deferred", "overridden"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "database" / "aida_decisions.db"
DB_PATH = Path(os.getenv("AIDA_DECISION_DB", DEFAULT_DB_PATH))

_lock = Lock()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_store() -> None:
    with _lock, _connect() as connection:
        connection.executescript(
            """
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
              created_at TEXT NOT NULL,
              UNIQUE(event_id)
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

            """
        )
        _add_column_if_missing(
            connection,
            table="recommendation_audit_events",
            column="scenario_id",
            definition="TEXT NOT NULL DEFAULT 'base'",
        )
        _add_column_if_missing(
            connection,
            table="demo_assignments",
            column="scenario_id",
            definition="TEXT NOT NULL DEFAULT 'base'",
        )
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_recommendation_audit_events_scenario_incident
              ON recommendation_audit_events (scenario_id, incident_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_demo_assignments_scenario_active
              ON demo_assignments (scenario_id, crew_id, status);
            """
        )


def _add_column_if_missing(
    connection: sqlite3.Connection,
    *,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    recommendation = json.loads(row["explanation_json"])
    return {
        "event_id": row["event_id"],
        "scenario_id": row["scenario_id"],
        "recommendation_id": row["recommendation_id"],
        "incident_id": row["incident_id"],
        "crew_id": row["crew_id"],
        "action": row["action"],
        "reason": row["reason"],
        "note": row["reason"],
        "recommendation": recommendation,
        "created_at": row["created_at"],
        "actor": row["actor"],
    }


def record_decision(
    *,
    scenario_id: str,
    incident_id: str,
    action: ActionStatus,
    recommendation: dict[str, Any],
    reason: str | None = None,
    actor: str = "demo-dispatcher",
) -> dict[str, Any]:
    init_store()

    crew = recommendation.get("recommended_crew") or {}
    crew_id = crew.get("crew_id")
    recommendation_id = str(recommendation.get("recommendation_id") or f"REC-{incident_id}-{crew_id or 'REVIEW'}")
    event_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with _lock, _connect() as connection:
        connection.execute(
            """
            INSERT INTO recommendation_audit_events (
              event_id, scenario_id, recommendation_id, incident_id, crew_id, action, reason,
              actor, confidence, explanation_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                scenario_id,
                recommendation_id,
                incident_id,
                crew_id,
                action,
                reason,
                actor,
                recommendation.get("confidence"),
                json.dumps(recommendation, sort_keys=True),
                created_at,
            ),
        )

        if action == "accepted" and crew_id:
            existing = connection.execute(
                """
                SELECT assignment_id
                FROM demo_assignments
                WHERE scenario_id = ? AND crew_id = ? AND status = 'active'
                """,
                (scenario_id, crew_id),
            ).fetchone()
            if not existing:
                connection.execute(
                    """
                    INSERT INTO demo_assignments (
                      assignment_id, scenario_id, incident_id, crew_id, status,
                      assigned_at, notes, decision_event_id
                    )
                    VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        f"ASG-DEMO-{uuid4().hex[:8].upper()}",
                        scenario_id,
                        incident_id,
                        crew_id,
                        created_at,
                        f"Accepted recommendation {recommendation_id}",
                        event_id,
                    ),
                )

    return {
        "event_id": event_id,
        "scenario_id": scenario_id,
        "recommendation_id": recommendation_id,
        "incident_id": incident_id,
        "crew_id": crew_id,
        "action": action,
        "reason": reason,
        "note": reason,
        "recommendation": recommendation,
        "created_at": created_at,
        "actor": actor,
    }


def recent_decisions(scenario_id: str, limit: int = 25) -> list[dict[str, Any]]:
    init_store()
    with _lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM recommendation_audit_events
            WHERE scenario_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (scenario_id, limit),
        ).fetchall()
    return [_row_to_event(row) for row in rows]


def latest_decisions_by_incident(scenario_id: str) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for event in recent_decisions(scenario_id, limit=500):
        decisions.setdefault(event["incident_id"], event)
    return decisions


def accepted_assignments(scenario_id: str) -> list[dict[str, Any]]:
    init_store()
    with _lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT assignment_id, scenario_id, incident_id, crew_id, status, assigned_at, notes
            FROM demo_assignments
            WHERE scenario_id = ? AND status = 'active'
            ORDER BY assigned_at ASC
            """,
            (scenario_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_decisions(scenario_id: str | None = None) -> None:
    init_store()
    with _lock, _connect() as connection:
        if scenario_id is None:
            connection.execute("DELETE FROM demo_assignments")
            connection.execute("DELETE FROM recommendation_audit_events")
        else:
            connection.execute("DELETE FROM demo_assignments WHERE scenario_id = ?", (scenario_id,))
            connection.execute("DELETE FROM recommendation_audit_events WHERE scenario_id = ?", (scenario_id,))
