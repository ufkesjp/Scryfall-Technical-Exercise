import gzip

from fetch_data import is_valid_gzip


def test_valid_gzip_accepted(tmp_path):
    p = tmp_path / "ok.gz"
    p.write_bytes(gzip.compress(b"hello\n" * 1000))
    assert is_valid_gzip(p)


def test_truncated_gzip_rejected(tmp_path):
    p = tmp_path / "bad.gz"
    p.write_bytes(gzip.compress(b"hello\n" * 1000)[:-10])
    assert not is_valid_gzip(p)
