"""Test the connection to the Scryfall API and download the Oracle Cards bulk data file. Verify it meets size requirements.

The download streams into a .part file that is renamed only once it is complete, so an interrupted run can never
leave a truncated oracle-cards.jsonl.gz behind. Re-running resumes the .part file with an HTTP Range request.
"""
import gzip
import json
import logging
import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BULK_URL = "https://api.scryfall.com/bulk-data/oracle-cards"
OUT_PATH = Path(__file__).parent / "data" / "oracle-cards.jsonl.gz"
MIN_BYTES = 10*1024*1024  # will use to verify >= 10MB file size
HEADERS = {"User-Agent": "ScryfallTechnicalExercise/1.0", "Accept": "application/json"}
TIMEOUT = (10, 60)  # (connect, read) seconds
RESUME_ATTEMPTS = 5  # extra tries when the connection drops mid-download
REQUIRED_KEYS = {"id", "oracle_id", "name"}  # every card line must have these

log = logging.getLogger(__name__)


def make_session() -> requests.Session:
    """Session that retries transient failures (rate limits and 5xx) with exponential backoff."""
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def is_valid_gzip(path: Path) -> bool:
    """True if path decompresses end to end (this also checks the gzip CRC and catches truncation)."""
    try:
        with gzip.open(path, "rb") as f:
            while f.read(1 << 20):
                pass
    except (OSError, EOFError):
        return False
    return True


def first_line_is_card(path: Path) -> bool:
    """True if the first line is a JSON object with the keys the pipeline needs (catches a gzipped error body)."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            card = json.loads(f.readline())
    except (OSError, EOFError, ValueError):  # ValueError covers bad JSON and bad UTF-8
        return False
    return isinstance(card, dict) and REQUIRED_KEYS <= card.keys()


def download(session: requests.Session, url: str, out_path: Path, expected_size: int | None = None) -> None:
    """Download url to out_path via out_path.part, resuming a partial file if one exists.

    expected_size is the compressed_size Scryfall reports in the bulk-data metadata.
    """
    part = out_path.with_name(out_path.name + ".part")
    for attempt in range(1, RESUME_ATTEMPTS + 1):
        offset = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with session.get(url, headers=headers, stream=True, timeout=TIMEOUT) as r:
                if r.status_code == 416:  # nothing left to fetch: the .part file is already complete
                    break
                r.raise_for_status()
                if offset and r.status_code != 206:  # server ignored Range, so start over
                    offset = 0
                log.info("Downloading %s (%s from byte %d)", url, "resuming" if offset else "starting", offset)
                with open(part, "ab" if offset else "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            break
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            log.warning("Download interrupted (attempt %d/%d): %s", attempt, RESUME_ATTEMPTS, e)
            if attempt == RESUME_ATTEMPTS:
                raise

    size = part.stat().st_size
    if size < MIN_BYTES:
        part.unlink()  # too small to be real, so don't resume it next time
        sys.exit(f"ERROR: File size is not at least {MIN_BYTES / 1024 / 1024:.2f} MB ({size} bytes)")
    # The size and gzip checks overlap on truncation but each catches something the other can't: the size check
    # catches a complete, valid file that isn't the one Scryfall advertised, while the gzip check catches a
    # corrupted file of the right size. MIN_BYTES above is the fallback when the metadata has no compressed_size.
    if expected_size is not None and size != expected_size:
        part.unlink()
        sys.exit(f"ERROR: Downloaded {size} bytes but Scryfall reports {expected_size}; deleted it, please re-run.")
    if not is_valid_gzip(part):
        part.unlink()  # corrupt, so start fresh next time rather than resuming it
        sys.exit("ERROR: Downloaded file is not a readable gzip; deleted it, please re-run.")
    if not first_line_is_card(part):
        part.unlink()
        sys.exit("ERROR: First line is not a card object; deleted the file, please re-run.")
    part.replace(out_path)  # atomic: out_path only ever holds a complete file


def main():
    session = make_session()
    resp = session.get(BULK_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    meta = resp.json()

    OUT_PATH.parent.mkdir(exist_ok=True)
    download(session, meta["jsonl_download_uri"], OUT_PATH, meta.get("compressed_size"))

    size = OUT_PATH.stat().st_size
    log.info("Saved %s (%.2f MB)", OUT_PATH, size / 1024 / 1024)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
