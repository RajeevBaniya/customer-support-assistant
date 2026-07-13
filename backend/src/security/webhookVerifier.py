import hashlib
import hmac
import time
from typing import Any

from src.observability.structuredLogger import get_logger
from src.shared.customExceptions import WebhookVerificationException

_TIMESTAMP_TOLERANCE_SECONDS = 300
_SVIX_VERSION = "v1"

logger = get_logger("security.webhook_verifier")


def _compute_signature(signing_key: str, msg_id: str, timestamp: str, body: bytes) -> str:
    secret = signing_key
    if secret.startswith("whsec_"):
        import base64

        secret = base64.b64decode(secret[len("whsec_") :]).hex()
        secret_bytes = bytes.fromhex(secret)
    else:
        secret_bytes = secret.encode("utf-8")

    to_sign = f"{msg_id}.{timestamp}.".encode() + body
    sig = hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()
    import base64

    return base64.b64encode(sig).decode("utf-8")


def verify_clerk_webhook(
    *,
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    signing_key: str,
) -> dict[str, Any]:
    if not svix_id or not svix_timestamp or not svix_signature:
        raise WebhookVerificationException("Missing required Svix headers")

    try:
        ts = int(svix_timestamp)
    except ValueError as exc:
        raise WebhookVerificationException("Invalid svix-timestamp value") from exc

    now = int(time.time())
    if abs(now - ts) > _TIMESTAMP_TOLERANCE_SECONDS:
        raise WebhookVerificationException(
            "Webhook timestamp is outside the accepted window",
            details={
                "svix_timestamp": svix_timestamp,
                "tolerance_seconds": _TIMESTAMP_TOLERANCE_SECONDS,
            },
        )

    expected_sig = _compute_signature(signing_key, svix_id, svix_timestamp, body)

    verified = False
    for provided in svix_signature.split(" "):
        version, _, sig_b64 = provided.partition(",")
        if version != _SVIX_VERSION:
            continue
        if hmac.compare_digest(sig_b64, expected_sig):
            verified = True
            break

    if not verified:
        logger.warning("webhook_signature_mismatch", svix_id=svix_id)
        raise WebhookVerificationException("Webhook signature verification failed")

    import json
    from typing import cast

    try:
        payload = cast(dict[str, Any], json.loads(body))
    except json.JSONDecodeError as exc:
        raise WebhookVerificationException("Webhook body is not valid JSON") from exc

    return payload
