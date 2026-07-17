from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.ragResponseBody import build_rag_payload
from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.orchestration.workflowOrchestrator import WorkflowOrchestrator
from src.orchestration.workflowRequest import WorkflowRequest
from src.schemas.ragSchemas import RagAskResponse
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
    orchestrator = WorkflowOrchestrator(session, settings)
    wf_req = WorkflowRequest(
        user_message=body.query.strip(),
        conversation_id=None,
        organization_id=user.organization_id,
        user_id=user.id,
        selected_document_ids=body.document_ids,
        stream=False,
    )
    wf_res = await orchestrator.execute(wf_req)

    top_k_used = 0
    if wf_res.retrieval_result:
        top_k_used = wf_res.retrieval_result.retrieval_metrics.top_k_used

    payload = RagAskResponse(
        answer=wf_res.response_result.assistant_text,
        citations=wf_res.response_result.citations,
        provider=wf_res.response_result.provider_used,
        retrieval_top_k=top_k_used,
    )
    out = format_success_response(build_rag_payload(payload), message="Rag")
    return JSONResponse(content=out)
