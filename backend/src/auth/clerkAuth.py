import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

import jwt
from jwt import PyJWKClient

from src.core.appEnvironment import AppEnvironment
from src.schemas.authSchemas import ClerkTokenPayload
from src.shared.customExceptions import AuthException


def _decode_hs256(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        options={"verify_signature": True, "require": ["exp", "sub"]},
    )


def _decode_rs256_sync(token: str, issuer: str) -> dict[str, Any]:
    normalized = issuer.rstrip("/")
    jwks_url = f"{normalized}/.well-known/jwks.json"
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=normalized,
        options={"verify_aud": False, "require": ["exp", "sub", "iss"]},
    )


def _exp_to_datetime(exp: Any) -> datetime:
    if isinstance(exp, datetime):
        return exp if exp.tzinfo else exp.replace(tzinfo=UTC)
    if isinstance(exp, int | float):
        return datetime.fromtimestamp(float(exp), tz=UTC)
    raise AuthException("Invalid token expiration")


def _payload_from_claims(claims: Mapping[str, Any], issuer: str) -> ClerkTokenPayload:
    sub = str(claims.get("sub") or "").strip()
    if not sub:
        raise AuthException("Invalid token subject")
    exp = claims.get("exp")
    expires_at = _exp_to_datetime(exp)
    email = claims.get("email")
    given = claims.get("given_name") or claims.get("first_name")
    family = claims.get("family_name") or claims.get("last_name")
    return ClerkTokenPayload(
        sub=sub,
        email=str(email) if email is not None else None,
        email_verified=cast(bool | None, claims.get("email_verified")),
        given_name=str(given) if given is not None else None,
        family_name=str(family) if family is not None else None,
        issuer=issuer,
        expires_at=expires_at,
    )


async def verify_bearer_token(raw_token: str, settings: AppEnvironment) -> ClerkTokenPayload:
    stripped = raw_token.strip()
    if not stripped:
        raise AuthException("Missing bearer token")
    env = settings.app_env.lower()
    if env == "test" and settings.test_jwt_secret:
        try:
            claims = _decode_hs256(stripped, settings.test_jwt_secret.strip())
        except jwt.PyJWTError as exc:
            raise AuthException("Invalid or expired token", details={"reason": str(exc)}) from exc
        return _payload_from_claims(claims, issuer="test")
    issuer = settings.clerk_jwt_issuer
    if not issuer or not str(issuer).strip():
        raise AuthException(
            "Auth is not configured",
            details={"reason": "missing_clerk_jwt_issuer"},
        )
    try:
        claims = await asyncio.to_thread(_decode_rs256_sync, stripped, str(issuer).strip())
    except jwt.PyJWTError as exc:
        raise AuthException("Invalid or expired token", details={"reason": str(exc)}) from exc
    resolved_issuer = str(claims.get("iss") or issuer).strip()
    return _payload_from_claims(claims, issuer=resolved_issuer)
