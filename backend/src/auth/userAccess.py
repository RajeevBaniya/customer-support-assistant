from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.authService import load_or_create_user
from core.appEnvironment import AppEnvironment
from database.databaseSession import get_db_session
from models.userModel import User
from schemas.authSchemas import ClerkTokenPayload
from shared.customExceptions import AuthException


def clerk_token_from_request(request: Request) -> ClerkTokenPayload:
    token = getattr(request.state, "clerk_token", None)
    if token is None:
        raise AuthException("Not authenticated")
    if not isinstance(token, ClerkTokenPayload):
        raise AuthException("Invalid auth state")
    return token


async def get_application_user(
    request: Request,
    token: ClerkTokenPayload = Depends(clerk_token_from_request),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    settings: AppEnvironment = request.app.state.settings
    return await load_or_create_user(session, settings, token)
