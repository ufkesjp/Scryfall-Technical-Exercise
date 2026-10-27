import gzip
from unittest.mock import MagicMock

import pytest

import fetch_data
from fetch_data import download, first_line_is_card, is_valid_gzip


def test_valid_gzip_accepted(tmp_path):
    p = tmp_path / "ok.gz"
    p.write_bytes(gzip.compress(b"hello\n" * 1000))
    assert is_valid_gzip(p)


def test_truncated_gzip_rejected(tmp_path):
    p = tmp_path / "bad.gz"
    p.write_bytes(gzip.compress(b"hello\n" * 1000)[:-10])
    assert not is_valid_gzip(p)


def test_first_line_card_accepted_and_error_body_rejected(tmp_path):
    ok, bad = tmp_path / "ok.gz", tmp_path / "bad.gz"
    ok.write_bytes(gzip.compress(b'{"id": "a", "oracle_id": "b", "name": "Llanowar Elves"}\n'))
    bad.write_bytes(gzip.compress(b'{"object": "error", "status": 429}\n'))
    assert first_line_is_card(ok)
    assert not first_line_is_card(bad)


def test_download_rejects_size_not_matching_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_data, "MIN_BYTES", 1)
    payload = gzip.compress(b'{"id": "a", "oracle_id": "b", "name": "x"}\n')
    response = MagicMock(status_code=200)
    response.__enter__.return_value = response
    response.iter_content.return_value = [payload]
    session = MagicMock(get=MagicMock(return_value=response))
    out = tmp_path / "cards.gz"
    with pytest.raises(SystemExit):
        download(session, "http://x", out, expected_size=len(payload) + 1)
    assert not out.exists() and not (tmp_path / "cards.gz.part").exists()
