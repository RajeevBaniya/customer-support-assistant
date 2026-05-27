from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from src.auth.userAccess import get_application_user
from src.models.userModel import User
from src.schemas.userSchemas import OrganizationSummaryResponse, UserProfileResponse
from src.shared.responseFormatter import format_success_response

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me")
async def user_me(user: User = Depends(get_application_user)) -> Response:
    payload = UserProfileResponse.model_validate(user)
    body = format_success_response(payload.model_dump(mode="json"), message="Profile")
    return JSONResponse(content=body)


@user_router.get("/organization")
async def user_organization(user: User = Depends(get_application_user)) -> Response:
    org = user.organization
    payload = OrganizationSummaryResponse.model_validate(org)
    body = format_success_response(payload.model_dump(mode="json"), message="Organization")
    return JSONResponse(content=body)
