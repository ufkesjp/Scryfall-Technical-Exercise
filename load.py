"""Load transformed cards into SQLite in batches. Safe to run repeatedly."""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Iterable

from transform import transform_card

log = logging.getLogger(__name__)

# Parents first. Reference rows (sets, keywords) use INSERT OR IGNORE: REPLACE would delete a row that
# cards still point at (foreign key error) and would hand keywords a new id.
# Re-loading a card uses INSERT OR REPLACE, which deletes the old row and cascades to its child rows,
# so stale keywords/types/colors from a previous load don't survive.
INSERTS = {
    "sets": "INSERT OR IGNORE INTO sets VALUES (?, ?, ?)",
    "keywords": "INSERT OR IGNORE INTO keywords (keyword) VALUES (?)",
    "cards": "INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    "card_keywords": (
        "INSERT OR IGNORE INTO card_keywords "
        "SELECT ?, keyword_id FROM keywords WHERE keyword = ?"
    ),
    "card_types": "INSERT OR IGNORE INTO card_types VALUES (?, ?, ?)",
    "card_color_identity": "INSERT OR IGNORE INTO card_color_identity VALUES (?, ?)",
}


def _flush(conn: sqlite3.Connection, buffers: dict[str, list[tuple]]) -> None:
    """Write buffered rows in one transaction (rolled back if anything fails), then clear them."""
    with conn:
        for table, sql in INSERTS.items():
            if buffers[table]:
                conn.executemany(sql, buffers[table])
    for rows in buffers.values():
        rows.clear()


def load(conn: sqlite3.Connection, cards: Iterable[dict[str, Any]], batch_size: int = 2000) -> int:
    """Transform and insert cards, committing every batch_size cards. Returns the number of cards loaded."""
    buffers: dict[str, list[tuple]] = {table: [] for table in INSERTS}
    count = 0
    for card in cards:
        for table, rows in transform_card(card).items():
            buffers[table].extend(rows)
        count += 1
        if count % batch_size == 0:
            _flush(conn, buffers)
            log.info("Loaded %d cards", count)
    _flush(conn, buffers)
    log.info("Loaded %d cards", count)
    return count
