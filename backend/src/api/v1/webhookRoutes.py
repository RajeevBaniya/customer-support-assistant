from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.authService import load_or_create_user
from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.schemas.authSchemas import ClerkTokenPayload
from src.security.auditLogger import audit_logger
from src.security.webhookVerifier import verify_clerk_webhook
from src.shared.customExceptions import BaseApplicationException, WebhookVerificationException
from src.shared.responseFormatter import format_error_response

webhook_router = APIRouter(tags=["webhooks"])

logger = get_logger("api.webhooks")

_SUPPORTED_EVENTS = frozenset({"user.created", "user.updated"})


async def _handle_user_event(
    payload: dict[str, Any],
    session: AsyncSession,
    settings: AppEnvironment,
) -> None:
    data = payload.get("data", {})
    clerk_user_id: str = data.get("id", "")
    if not clerk_user_id:
        return

    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")
    email: str | None = None
    for addr in email_addresses:
        if addr.get("id") == primary_email_id:
            email = addr.get("email_address")
            break

    token = ClerkTokenPayload(
        sub=clerk_user_id,
        email=email,
        email_verified=True,
        given_name=data.get("first_name"),
        family_name=data.get("last_name"),
        issuer=settings.clerk_jwt_issuer or "",
        expires_at=datetime.fromisoformat("2099-01-01T00:00:00+00:00"),
    )
    await load_or_create_user(session, settings, token)


@webhook_router.post("/api/v1/webhooks/clerk")
async def clerk_webhook(request: Request) -> Response:
    settings: AppEnvironment = request.app.state.settings

    signing_key = settings.clerk_webhook_signing_key
    if not signing_key or not str(signing_key).strip():
        logger.error("clerk_webhook_signing_key_not_configured")
        return JSONResponse(status_code=503, content={"error": "Webhook not configured"})

    body = await request.body()
    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    try:
        payload = verify_clerk_webhook(
            body=body,
            svix_id=svix_id,
            svix_timestamp=svix_timestamp,
            svix_signature=svix_signature,
            signing_key=str(signing_key),
        )
    except WebhookVerificationException as exc:
        audit_logger.log_webhook_event(
            event="clerk_webhook_rejected",
            svix_id=svix_id or None,
            outcome="rejected",
            reason=exc.message,
        )
        error_body = format_error_response(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(status_code=400, content=error_body)

    event_type: str = payload.get("type", "")
    audit_logger.log_webhook_event(
        event="clerk_webhook_received",
        svix_id=svix_id or None,
        outcome="accepted",
        event_type=event_type,
    )

    if event_type in _SUPPORTED_EVENTS:
        session_factory = request.app.state.async_session_factory
        async with session_factory() as session:
            try:
                await _handle_user_event(payload, session, settings)
                await session.commit()
            except BaseApplicationException as exc:
                await session.rollback()
                logger.error(
                    "clerk_webhook_user_sync_failed",
                    event_type=event_type,
                    error=exc.message,
                )

    return JSONResponse(status_code=200, content={"received": True})
