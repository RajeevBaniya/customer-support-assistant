from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.retrieval.retrievalService import RetrievalService
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.shared.responseFormatter import format_success_response

retrieval_router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@retrieval_router.post("/search")
async def retrieval_search(
    request: Request,
    body: RetrievalSearchRequest,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = RetrievalService.from_request(session, settings)
    payload = await service.search(organization_id=user.organization_id, body=body)
    out = format_success_response(payload.model_dump(mode="json"), message="Retrieval")
    return JSONResponse(content=out)
