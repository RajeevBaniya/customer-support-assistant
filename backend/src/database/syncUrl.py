def to_psycopg(async_url: str) -> str:
    normalized = async_url.strip()
    if not normalized.startswith("postgresql+asyncpg"):
        raise ValueError("DATABASE_URL must use postgresql+asyncpg for async SQLAlchemy")
    return normalized.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
