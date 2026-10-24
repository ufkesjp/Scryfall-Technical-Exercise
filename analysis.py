"""Run the queries in queries.sql and print the results; question 2 is also grouped and charted with pandas.

Questions 1, 3 and 4 are pure SQL run from Python. See queries.sql for the SQL and the "why it matters" notes.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

from db import DEFAULT_DB, connect

QUERIES_PATH = Path(__file__).resolve().parent / "queries.sql"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def load_queries(path: Path = QUERIES_PATH) -> dict[str, dict[str, str]]:
    """Split queries.sql on its '-- name:' lines into {name: {title, why, finding, sql}}."""
    parts = re.split(r"^-- name: (\w+)\n", path.read_text(), flags=re.MULTILINE)
    queries = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        meta = dict(re.findall(r"^-- (title|why|finding): (.*)$", body, flags=re.MULTILINE))
        sql = re.sub(r"^-- (title|why|finding): .*\n", "", body, flags=re.MULTILINE).strip()
        queries[name] = {**meta, "sql": sql}
    return queries


def show(q: dict[str, str], df: pd.DataFrame) -> None:
    print(f"\n=== {q['title']} ===\nWhy it matters: {q['why']}\n\nSQL:\n{q['sql']}\n\n{df.to_string(index=False)}\n\nFinding: {q['finding']}")


def chart_cmc(df: pd.DataFrame) -> Path:
    import matplotlib
    matplotlib.use("Agg")  # write to a file, no window needed
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(df["colors"].astype(str), df["avg_cmc"], color="#4c78a8")
    ax.set_xlabel("Colors in color identity (0 = colorless)")
    ax.set_ylabel("Average mana value")
    ax.set_title("Average mana value by number of colors (nonland cards)")
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "avg_cmc_by_color_count.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def run(conn: sqlite3.Connection) -> None:
    """Print all four analyses and save the chart for question 3."""
    queries = load_queries()
    conn.executescript(queries.pop("setup")["sql"])
    for name, q in queries.items():
        df = pd.read_sql_query(q["sql"], conn)
        if name == "cmc_by_color_count":
            df = (df.groupby("colors")["cmc"].agg(cards="count", avg_cmc="mean", median_cmc="median")
                  .round(2).reset_index())
            show(q, df)
            print(f"\nChart saved to {chart_cmc(df)}")
        else:
            show(q, df)


if __name__ == "__main__":
    conn = connect(DEFAULT_DB)
    try:
        run(conn)
    finally:
        conn.close()
