from urllib.parse import parse_qsl, urlparse

from src.database.urlNormalization import resolve_database_urls


def test_async_url_strips_sslmode_channel_binding_sync_keeps_them() -> None:
    raw = (
        "postgresql+asyncpg://u:p@ep.test.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require&options=-c%20search_path%3Dpublic"
    )
    r = resolve_database_urls(raw)
    assert "sslmode=require" in r.sync_alembic_url
    assert "channel_binding=require" in r.sync_alembic_url
    assert r.sync_alembic_url.startswith("postgresql+psycopg://")
    async_q = urlparse(r.async_sqlalchemy_url).query
    keys = {k.lower() for k, _ in parse_qsl(async_q, keep_blank_values=True)}
    assert "sslmode" not in keys
    assert "channel_binding" not in keys
    assert "options" in keys
    assert r.async_connect_args == {"ssl": True}


def test_connect_args_ssl_true_for_ssl_query_flag() -> None:
    raw = "postgresql+asyncpg://u:p@h/db?ssl=true"
    r = resolve_database_urls(raw)
    assert r.async_connect_args == {"ssl": True}
    assert "ssl=true" not in urlparse(r.async_sqlalchemy_url).query.lower()


def test_connect_args_empty_without_ssl_hints() -> None:
    raw = "postgresql+asyncpg://u:p@h/db"
    r = resolve_database_urls(raw)
    assert r.async_connect_args == {}
    assert r.async_sqlalchemy_url == raw
