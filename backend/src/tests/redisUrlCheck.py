from src.realtime.redis_connection import normalize_redis_url_for_tls


def test_upstash_redis_scheme_upgraded_to_rediss() -> None:
    raw = "redis://default:secret@my-db-12345.upstash.io:6379"
    out = normalize_redis_url_for_tls(raw)
    assert out.startswith("rediss://")
    assert "my-db-12345.upstash.io" in out


def test_local_redis_url_unchanged() -> None:
    raw = "redis://127.0.0.1:6379/0"
    assert normalize_redis_url_for_tls(raw) == raw


def test_rediss_upstash_unchanged() -> None:
    raw = "rediss://default:secret@host.upstash.io:6379"
    assert normalize_redis_url_for_tls(raw) == raw
