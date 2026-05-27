from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.authService import load_or_create_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.schemas.authSchemas import ClerkTokenPayload
from src.shared.customExceptions import AuthException


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
