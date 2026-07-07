import base64
import hashlib
import hmac
import json
import time

import pytest

from src.security.webhookVerifier import verify_clerk_webhook
from src.shared.customExceptions import WebhookVerificationException


def _make_key() -> str:
    raw = b"test_secret_bytes_for_unit_tests!"
    return "whsec_" + base64.b64encode(raw).decode()


def _sign(signing_key: str, svix_id: str, timestamp: str, body: bytes) -> str:
    secret = signing_key
    if secret.startswith("whsec_"):
        secret_bytes = base64.b64decode(secret[len("whsec_") :])
    else:
        secret_bytes = secret.encode()

    to_sign = f"{svix_id}.{timestamp}.".encode() + body
    sig = hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()
    return "v1," + base64.b64encode(sig).decode()


def _now_ts() -> str:
    return str(int(time.time()))


def test_valid_webhook_signature_accepted():
    key = _make_key()
    body = json.dumps({"type": "user.created", "data": {"id": "user_abc"}}).encode()
    svix_id = "msg_01"
    ts = _now_ts()
    sig = _sign(key, svix_id, ts, body)

    payload = verify_clerk_webhook(
        body=body,
        svix_id=svix_id,
        svix_timestamp=ts,
        svix_signature=sig,
        signing_key=key,
    )
    assert payload["type"] == "user.created"


def test_invalid_signature_raises():
    key = _make_key()
    body = json.dumps({"type": "user.created"}).encode()
    ts = _now_ts()

    with pytest.raises(WebhookVerificationException) as exc_info:
        verify_clerk_webhook(
            body=body,
            svix_id="msg_01",
            svix_timestamp=ts,
            svix_signature="v1,invalidsignature==",
            signing_key=key,
        )
    assert exc_info.value.status_code == 400


def test_old_timestamp_raises():
    key = _make_key()
    body = json.dumps({"type": "user.created"}).encode()
    stale_ts = str(int(time.time()) - 400)
    sig = _sign(key, "msg_01", stale_ts, body)

    with pytest.raises(WebhookVerificationException) as exc_info:
        verify_clerk_webhook(
            body=body,
            svix_id="msg_01",
            svix_timestamp=stale_ts,
            svix_signature=sig,
            signing_key=key,
        )
    assert "window" in exc_info.value.message.lower()


def test_missing_headers_raise():
    with pytest.raises(WebhookVerificationException):
        verify_clerk_webhook(
            body=b"{}",
            svix_id="",
            svix_timestamp="",
            svix_signature="",
            signing_key=_make_key(),
        )


def test_invalid_json_body_raises():
    key = _make_key()
    body = b"not json"
    ts = _now_ts()
    sig = _sign(key, "msg_01", ts, body)

    with pytest.raises(WebhookVerificationException) as exc_info:
        verify_clerk_webhook(
            body=body,
            svix_id="msg_01",
            svix_timestamp=ts,
            svix_signature=sig,
            signing_key=key,
        )
    assert "json" in exc_info.value.message.lower()
