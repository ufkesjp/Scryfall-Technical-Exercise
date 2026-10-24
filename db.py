"""SQLite connection helper."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = Path(__file__).resolve().parent / "data" / "scryfall.db"


def connect(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    """Open the DB with foreign keys on, applying schema.sql if it's a fresh file."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cards'"
    ).fetchone()
    # schema.sql uses plain CREATE TABLE, so only apply it once. CREATE TABLE IF NOT EXISTS (with
    # INSERT OR IGNORE for the reference rows) would be more resilient, but this DB is a disposable
    # build artifact regenerated from the source file, so I kept the DDL simple. If the schema
    # changes, delete data/scryfall.db and rebuild rather than migrating.
    if not exists:
        conn.executescript(SCHEMA_PATH.read_text())
    return conn
