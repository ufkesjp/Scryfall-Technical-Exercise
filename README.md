# Scryfall Analytics Exercise

A Python 3 + SQLite pipeline that downloads Scryfall's Oracle Cards bulk file, loads it into a normalized SQLite database, and answers four analytical questions with a mix of SQL and pandas.

## Why this datasource?
This project uses the "Oracle Cards" file from [Scryfall's bulk data API](https://scryfall.com/docs/api/bulk-data). It has one JSON object per unique Magic: The Gathering card (about 39,000 cards, roughly 25 MB gzipped and 200 MB uncompressed), so it is well over the 10 MB minimum. I picked it because I enjoy the game and expected plenty of fun, answerable questions about the cards once they were in a relational database.

## Prerequisites
- Python 3.11 or newer (CI runs 3.12; a clean-clone run also worked on 3.14)
- Internet access for the first run (about 25 MB download)

## Setup and run
```bash
git clone https://github.com/ufkesjp/Scryfall-Technical-Exercise.git
cd Scryfall-Technical-Exercise
python3 -m venv .venv          # use python3 if python isn't found (common on macOS)
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Once the venv is active, `python` works for the remaining commands.

`python main.py` does everything end to end: downloads the file to `data/` (skipped if already present), builds `data/scryfall.db` from `schema.sql`, loads the cards, then prints the analyses and saves the chart. A first run took about 25 seconds in a clean-clone test, including the 25 MB download, and a re-run takes about 6 seconds.

A successful run prints `Loaded N cards` progress lines, then four sections headed `=== 1. ... ===` through `=== 4. ... ===`, and ends with question 4's "Finding" line. Question 2 also prints `Chart saved to .../output/avg_cmc_by_color_count.png`.

Options:
- `--file PATH` loads a local `.jsonl.gz` instead of downloading.
- `--db PATH` builds the database somewhere other than `data/scryfall.db`.

To pick up a newer daily export, delete `data/oracle-cards.jsonl.gz` and run again. To change the schema, delete `data/scryfall.db` and rebuild (`schema.sql` is idempotent and runs on every connect, but `IF NOT EXISTS` won't alter existing tables).

Run the tests with `python -m pytest`.

## Where to see the answers
- **Terminal output:** each question prints its title, why it matters, the SQL, a results table and a short finding.
- **Chart:** `output/avg_cmc_by_color_count.png` (question 2).
- **SQL:** [queries.sql](queries.sql) holds every query with its rationale. [analysis.py](analysis.py) runs them.

| # | Question | Method |
|---|---|---|
| 1 | How does the rarity mix differ by kind of set? | pure SQL |
| 2 | Does mana cost grow with the number of colors? | SQL + pandas + matplotlib chart |
| 3 | Which creature types belong to which color? | pure SQL |
| 4 | How many new cards does each era of the game contribute? | pure SQL |

## Project layout
| File | Purpose |
|---|---|
| [main.py](main.py) | Single entry point: fetch, load, analyze |
| [fetch_data.py](fetch_data.py) | Resolves the current file URL and downloads it safely |
| [transform.py](transform.py) | Streams the file and flattens each card into rows per table |
| [load.py](load.py) | Batched, transactional, repeatable inserts |
| [db.py](db.py) | SQLite connection; applies `schema.sql` (idempotent) on every connect |
| [schema.sql](schema.sql) | DDL, reference-row seeds and indexes |
| [analysis.py](analysis.py), [queries.sql](queries.sql) | The four questions |
| [make_er_diagram.py](make_er_diagram.py) | Generates the ER diagram from `schema.sql` |
| [tests/](tests) | pytest suite |

## Schema
See the [ER diagram](docs/er_diagram.md) (Mermaid, rendered by GitHub), generated from `schema.sql` with `python make_er_diagram.py`.

- `cards` holds one row per Oracle ID. `sets` and `rarities` are parents of `cards`.
- `card_keywords`, `card_types` and `card_color_identity` are child tables, deleted along with their card (`ON DELETE CASCADE`).
- `rarities` (common to mythic) and `colors` (WUBRG) are seeded reference tables, so results sort by game order instead of alphabetically.
- Two covering indexes on `cards` serve questions 1 and 4. They were chosen by checking `EXPLAIN QUERY PLAN` and timings. Indexes on the child tables made question 3 slower, so there are none.
- Power and toughness are text because of values like `*` and `1+*`.

## Design notes
- **Idempotent load.** Running twice gives identical row counts (verified on the 2026-10-23 export; the file refreshes daily, so your numbers will differ slightly: 38,987 cards, 588 sets, 895 keywords, 25,139 card-keyword rows, 85,810 type rows, 40,193 color-identity rows, and `PRAGMA foreign_key_check` is clean). Cards use `INSERT OR REPLACE`, which cascades to the old child rows so stale keywords or types don't survive. Sets and keywords use `INSERT OR IGNORE`, because replacing a parent row would break foreign keys and renumber keyword ids.
- **Batching.** Rows are buffered and written 2,000 cards at a time, one transaction per batch, so a failure rolls back that batch only.
- **Safe download.** The file streams into a `.part` file with retries, backoff and timeouts, and resumes after an interrupted connection. It is checked as a readable gzip of at least 10 MB, then renamed atomically, so a bad file is never left in place.
- **Multi-faced cards.** These have no top-level `mana_cost`, so it is NULL for them. Their `type_line` is the faces joined with ` // `, and `card_types` includes the parts of every face, de-duplicated.
- **"Playable" filter.** The schema has no legalities, so the analyses exclude non-deck objects by `layout` (tokens, art cards, emblems, vanguard, scheme, planar, archenemy) through a temporary view. Digital-only cards (for example Alchemy) are kept.

## Known quirks
- **API field change.** The bulk-data metadata no longer has `download_uri`. The pipeline reads `jsonl_download_uri` (gzipped JSON Lines) and resolves it at runtime, because the file URL rotates daily.
- **Representative printing.** `set_code`, `rarity` and `released_at` describe the one printing Scryfall chose for each card, not its whole history. Reprinted old cards can show a newer date, which makes the earliest eras in question 4 look smaller than they were.
- **Joke cards.** A few cards have absurd mana values (for example 1,000,000), so question 2 excludes cmc of 100 or more.
- **Tokens and art cards** are kept in the database but filtered out of the analyses.
- **Rate limits.** Scryfall asks for a descriptive `User-Agent` and polite request rates. The pipeline sends one, makes only two requests per run, and retries 429/5xx responses with backoff.
- **Reused download.** An existing `data/oracle-cards.jsonl.gz` is reused without a freshness check.
- **Log noise.** pandas/matplotlib may print a harmless "Using categorical units" INFO line during question 2.
