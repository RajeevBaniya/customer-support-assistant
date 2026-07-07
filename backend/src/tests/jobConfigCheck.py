from src.core.appEnvironment import AppEnvironment
from src.jobs.jobConfig import celery_broker_url, celery_result_backend_url


def test_celery_urls_append_ssl_cert_reqs_for_rediss() -> None:
    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/recallstack",
        REDIS_URL="rediss://default:secret@example.upstash.io:6379",
    )
    b = celery_broker_url(settings)
    assert b is not None
    assert "ssl_cert_reqs=CERT_NONE" in b
    r = celery_result_backend_url(settings)
    assert r is not None
    assert "ssl_cert_reqs=CERT_NONE" in r
