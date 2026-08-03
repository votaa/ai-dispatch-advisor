from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

ActionStatus = Literal["accepted", "modified", "deferred", "overridden"]

_actions: list[dict[str, Any]] = []
_lock = Lock()


def record_action(
    *,
    incident_id: str,
    action: ActionStatus,
    recommendation: dict[str, Any],
    note: str | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": str(uuid4()),
        "incident_id": incident_id,
        "action": action,
        "note": note,
        "recommendation": recommendation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor": "demo-dispatcher",
    }

    with _lock:
        _actions.insert(0, event)

    return event


def recent_actions(limit: int = 25) -> list[dict[str, Any]]:
    with _lock:
        return list(_actions[:limit])


def clear_actions() -> None:
    with _lock:
        _actions.clear()
