"""Download the Scryfall Oracle Cards file (if needed), load it into SQLite, and run the analysis."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import analysis
import fetch_data
from db import DEFAULT_DB, connect
from load import load
from transform import read_cards


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="load this local .jsonl.gz instead of downloading")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite file to build (default: %(default)s)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    path = args.file
    if path is None:
        path = fetch_data.OUT_PATH
        if not path.exists():  # an existing file is reused; delete it to pick up a newer daily export
            fetch_data.main()

    conn = connect(args.db)
    try:
        load(conn, read_cards(path))
        analysis.run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
