"""Generate docs/er_diagram.md (a Mermaid erDiagram) by building schema.sql in memory and reading its structure."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from db import SCHEMA_PATH

OUT_PATH = Path(__file__).resolve().parent / "docs" / "er_diagram.md"

HEADER = """# Entity-relationship diagram

Generated from [schema.sql](../schema.sql) by `make_er_diagram.py`; re-run it after any schema change.

```mermaid
"""


def build_diagram(conn: sqlite3.Connection) -> str:
    """Return a Mermaid erDiagram for every table in conn, using PRAGMAs for columns, keys and relationships."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    relationships, entities = [], []
    for table in tables:
        fks = {fk[3]: fk[2] for fk in conn.execute(f"PRAGMA foreign_key_list({table})")}   # column -> parent table
        unique = set()
        for idx in conn.execute(f"PRAGMA index_list({table})"):
            cols = [c[2] for c in conn.execute(f"PRAGMA index_info({idx[1]})")]
            if idx[2] and idx[3] == "u" and len(cols) == 1:   # single-column UNIQUE constraint
                unique.add(cols[0])
        lines = []
        for _, name, col_type, _, _, pk in conn.execute(f"PRAGMA table_info({table})"):
            keys = [k for k, hit in (("PK", pk), ("FK", name in fks), ("UK", name in unique)) if hit]
            lines.append(f"        {col_type} {name} {', '.join(keys)}".rstrip())
        entities.append(f"    {table} {{\n" + "\n".join(lines) + "\n    }")
        relationships += [f"    {parent} ||--o{{ {table} : \"{col}\"" for col, parent in fks.items()]
    return "erDiagram\n" + "\n".join(relationships) + "\n\n" + "\n".join(entities) + "\n"


def main() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(HEADER + build_diagram(conn) + "```\n")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
