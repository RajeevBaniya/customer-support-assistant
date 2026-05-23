from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from auth.authService import auth_me_view
from auth.userAccess import clerk_token_from_request
from schemas.authSchemas import AuthMeResponse, ClerkTokenPayload
from shared.responseFormatter import format_success_response

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/me")
async def auth_me(
    token: ClerkTokenPayload = Depends(clerk_token_from_request),
) -> Response:
    payload = AuthMeResponse.model_validate(auth_me_view(token))
    body = format_success_response(payload.model_dump(mode="json"), message="Authenticated")
    return JSONResponse(content=body)
