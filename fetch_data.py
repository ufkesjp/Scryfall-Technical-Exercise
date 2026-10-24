"""Test the connection to the Scryfall API and download the Oracle Cards bulk data file. Verify it meets size requirements."""
import sys
from pathlib import Path
import requests

BULK_URL = "https://api.scryfall.com/bulk-data/oracle-cards"
OUT_PATH = Path(__file__).parent / "data" / "oracle-cards.jsonl.gz"
MIN_BYTES = 10*1024*1024  # will use to verify >= 10MB file size
HEADERS = {"User-Agent": "ScryfallTechnicalExercise/1.0", "Accept": "application/json"}

def main():
    resp = requests.get(BULK_URL, headers=HEADERS, timeout = 30)
    resp.raise_for_status()
    download_uri= resp.json()["jsonl_download_uri"]

    OUT_PATH.parent.mkdir(exist_ok=True)
    print(f"Downloading {download_uri}")
    with requests.get(download_uri, headers=HEADERS, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(OUT_PATH, "wb") as f:
            for chunk in r.iter_content(1 <<20):
                f.write(chunk)

    size = OUT_PATH.stat().st_size
    print(f"Saved {OUT_PATH} ({size / 1024 / 1024:.2f} MB)")
    if size < MIN_BYTES:
        sys.exit(f"WARNING: File size is not at least {MIN_BYTES / 1024 / 1024:.2f} MB ({size} bytes)")
    print("OK: File size meets minimum requirements.")

if __name__ == "__main__":
    main()