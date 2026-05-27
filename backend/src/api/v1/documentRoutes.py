from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.documents.documentService import DocumentService
from src.models.userModel import User
from src.shared.responseFormatter import format_success_response

document_router = APIRouter(prefix="/documents", tags=["documents"])


@document_router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = DocumentService.from_request(session, settings)
    payload = await service.upload(upload=file, actor=user)
    body = format_success_response(payload.model_dump(mode="json"), message="Uploaded")
    return JSONResponse(content=body)


@document_router.get("")
async def list_documents(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = DocumentService.from_request(session, settings)
    payload = await service.list_for_actor(actor=user, limit=limit, offset=offset)
    body = format_success_response(payload.model_dump(mode="json"), message="Documents")
    return JSONResponse(content=body)


@document_router.post("/{document_id}/cancel-ingestion")
async def cancel_document_ingestion(
    request: Request,
    document_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = DocumentService.from_request(session, settings)
    payload = await service.cancel_ingestion(actor=user, document_id=document_id)
    body = format_success_response(payload.model_dump(mode="json"), message="Ingestion cancel")
    return JSONResponse(content=body)


@document_router.get("/{document_id}")
async def get_document(
    request: Request,
    document_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = DocumentService.from_request(session, settings)
    payload = await service.get_for_actor(actor=user, document_id=document_id)
    body = format_success_response(payload.model_dump(mode="json"), message="Document")
    return JSONResponse(content=body)
