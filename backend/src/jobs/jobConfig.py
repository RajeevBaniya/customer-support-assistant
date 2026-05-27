from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.core.appEnvironment import AppEnvironment
from src.realtime.redis_connection import normalize_redis_url_for_tls


def _celery_rediss_ssl_query(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "rediss":
        return url.strip()
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "ssl_cert_reqs" not in q:
        q["ssl_cert_reqs"] = "CERT_NONE"
    return urlunparse(parsed._replace(query=urlencode(q)))


def _resolved_redis(settings: AppEnvironment) -> str | None:
    u = settings.redis_url
    if u is None or not str(u).strip():
        return None
    return _celery_rediss_ssl_query(normalize_redis_url_for_tls(str(u).strip()))


def celery_broker_url(settings: AppEnvironment) -> str | None:
    raw = settings.celery_broker_url
    if raw is not None and str(raw).strip():
        return _celery_rediss_ssl_query(normalize_redis_url_for_tls(str(raw).strip()))
    return _resolved_redis(settings)


def celery_result_backend_url(settings: AppEnvironment) -> str | None:
    raw = settings.celery_result_backend
    if raw is not None and str(raw).strip():
        return _celery_rediss_ssl_query(normalize_redis_url_for_tls(str(raw).strip()))
    return _resolved_redis(settings)


def build_celery_conf(settings: AppEnvironment) -> dict[str, Any]:
    broker = celery_broker_url(settings)
    backend = celery_result_backend_url(settings)
    return {
        "broker_url": broker,
        "result_backend": backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_track_started": True,
        "broker_connection_retry_on_startup": True,
        "worker_prefetch_multiplier": 2,
        "task_default_queue": "recallstack_default",
        "result_backend_transport_options": {
            "retry_on_timeout": True,
        },
    }
