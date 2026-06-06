from src.core.appEnvironment import AppEnvironment


def security_health_bundle(settings: AppEnvironment) -> dict[str, object]:
    rate_limiting_configured = bool(settings.redis_url and str(settings.redis_url).strip())
    webhook_signing_configured = bool(
        settings.clerk_webhook_signing_key and str(settings.clerk_webhook_signing_key).strip()
    )

    return {
        "rate_limiting_configured": rate_limiting_configured,
        "webhook_signing_configured": webhook_signing_configured,
        "secure_headers_active": True,
        "file_content_scanning_active": True,
    }
