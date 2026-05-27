from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_ASYNC_SCHEME = "postgresql+asyncpg"
_SYNC_SCHEME = "postgresql+psycopg"


@dataclass(frozen=True)
class ResolvedDatabaseUrls:
    async_sqlalchemy_url: str
    sync_alembic_url: str
    async_connect_args: dict[str, Any]


def resolve_database_urls(raw_database_url: str) -> ResolvedDatabaseUrls:
    normalized = raw_database_url.strip()
    if not normalized.startswith(f"{_ASYNC_SCHEME}://"):
        raise ValueError("DATABASE_URL must use postgresql+asyncpg for async SQLAlchemy")

    parsed = urlparse(normalized)
    if parsed.scheme != _ASYNC_SCHEME:
        raise ValueError("DATABASE_URL must use postgresql+asyncpg for async SQLAlchemy")

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    lowered = {k.lower(): v for k, v in pairs}
    sslmode = (lowered.get("sslmode") or "").strip().lower()
    ssl_flag = (lowered.get("ssl") or "").strip().lower()

    connect: dict[str, Any] = {}
    if sslmode in {"require", "verify-ca", "verify-full"}:
        connect["ssl"] = True
    elif ssl_flag in {"true", "1", "on"}:
        connect["ssl"] = True

    drop_keys = {"sslmode", "channel_binding"}
    if connect.get("ssl") is True:
        drop_keys.add("ssl")
    async_pairs = [(k, v) for k, v in pairs if k.lower() not in drop_keys]
    async_query = urlencode(async_pairs, doseq=True)
    async_parsed = parsed._replace(query=async_query)
    async_sqlalchemy_url = urlunparse(async_parsed)

    sync_parsed = parsed._replace(scheme=_SYNC_SCHEME)
    sync_alembic_url = urlunparse(sync_parsed)

    return ResolvedDatabaseUrls(
        async_sqlalchemy_url=async_sqlalchemy_url,
        sync_alembic_url=sync_alembic_url,
        async_connect_args=connect,
    )
