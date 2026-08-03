from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "database" / "aida.db"
SCHEMA_PATH = REPO_ROOT / "database" / "schema.sql"
DATA_DIR = REPO_ROOT / "data" / "scenarios" / "base"

TABLE_FILES = {
    "incidents": "PendingIncidents.csv",
    "crews": "Crews.csv",
    "assignments": "Assignments.csv",
}


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        for table, filename in TABLE_FILES.items():
            path = DATA_DIR / filename
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            column_list = ", ".join(columns)
            values = [[row[column] for column in columns] for row in rows]
            connection.executemany(
                f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
                values,
            )

    print(f"Created {DB_PATH}")


if __name__ == "__main__":
    main()

