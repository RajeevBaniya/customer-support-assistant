from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.ragResponseBody import build_rag_payload
from src.ai.ragService import RagService
from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.security.rateLimitDependency import rate_limited
from src.shared.responseFormatter import format_success_response

rag_router = APIRouter(prefix="/rag", tags=["rag"])

_rate_limit_ask = rate_limited("rag_ask", lambda s: s.rate_limit_rag_ask)


@rag_router.post("/ask", dependencies=[Depends(_rate_limit_ask)])
async def rag_ask(
    request: Request,
    body: RetrievalSearchRequest,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = RagService.from_request(session, settings)
    payload = await service.ask(organization_id=user.organization_id, body=body)
    out = format_success_response(build_rag_payload(payload), message="Rag")
    return JSONResponse(content=out)
