"""SQLite connection helper."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = Path(__file__).resolve().parent / "data" / "scryfall.db"


def connect(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    """Open the DB with foreign keys on, applying schema.sql (idempotently)."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    # schema.sql is idempotent, so it's safe to run on every connect. If a table's definition changes, delete the DB and rebuild; IF NOT EXISTS won't alter existing tables.
    conn.executescript(SCHEMA_PATH.read_text())
    return conn
