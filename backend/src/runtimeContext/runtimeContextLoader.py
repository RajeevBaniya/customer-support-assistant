"""RuntimeContextLoader responsible for fetching, validating, and assembling runtime state."""

from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.runtimeContext.runtimeContext import RuntimeContext, WorkspaceContext
from src.runtimeContext.runtimeContextBuilder import RuntimeContextBuilder
from src.runtimeTools.conversationTool import (
    ConversationTool,
    ListRecentMessagesRequest,
    LoadConversationRequest,
)
from src.runtimeTools.sessionTool import LoadOrganizationRequest, LoadUserRequest, SessionTool
from src.runtimeTools.storageTool import LoadDocumentRequest, StorageTool
from src.shared.customExceptions import ResourceNotFoundException

logger = get_logger("runtime_context.loader")


class RuntimeContextLoader:
    """Coordinates fetching and validation of context states."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._settings = settings
        self._conversation_tool = ConversationTool(session, settings)
        self._session_tool = SessionTool(session, settings)
        self._storage_tool = StorageTool(session, settings)

    async def load(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        conversation_id: UUID | None,
        query: str,
        top_k: int,
        document_ids: list[UUID] | None = None,
    ) -> RuntimeContext:
        """Assembles complete RuntimeContext by fetching state through Runtime Tools."""
        start_time = perf_counter()
        logger.info(
            "context_loading_started",
            user_id=str(user_id),
            organization_id=str(organization_id),
            conversation_id=str(conversation_id) if conversation_id else None,
        )

        try:
            # 1. Load Session Context
            user = await self._session_tool.load_user(LoadUserRequest(user_id=user_id))
            if user is None:
                logger.warning(
                    "context_loading_validation_failed",
                    reason="user_not_found",
                    user_id=str(user_id),
                )
                raise ResourceNotFoundException("User not found", details={"user_id": user_id})

            org = await self._session_tool.load_organization(
                LoadOrganizationRequest(organization_id=organization_id)
            )
            if org is None:
                logger.warning(
                    "context_loading_validation_failed",
                    reason="organization_not_found",
                    organization_id=str(organization_id),
                )
                raise ResourceNotFoundException(
                    "Organization not found",
                    details={"organization_id": organization_id},
                )

            if user.organization_id != organization_id:
                logger.warning(
                    "context_loading_validation_failed",
                    reason="organization_mismatch",
                    user_id=str(user_id),
                    organization_id=str(organization_id),
                )
                raise ResourceNotFoundException("User does not belong to organization")

            session_context = RuntimeContextBuilder.build_session(org, user)

            # 2. Load Conversation Context
            conversation_context = None
            if conversation_id is not None:
                conversation = await self._conversation_tool.load_conversation(
                    LoadConversationRequest(
                        conversation_id=conversation_id,
                        organization_id=organization_id,
                        user_id=user_id,
                    )
                )
                if conversation is None:
                    logger.warning(
                        "context_loading_validation_failed",
                        reason="conversation_not_found",
                        conversation_id=str(conversation_id),
                    )
                    raise ResourceNotFoundException("Conversation not found")

                messages = await self._conversation_tool.list_recent_messages(
                    ListRecentMessagesRequest(
                        conversation_id=conversation_id,
                        limit=self._settings.chat_history_max_messages,
                    )
                )
                # Keep chronological ordering for Planning Context
                messages_ordered = list(reversed(messages))
                conversation_context = RuntimeContextBuilder.build_conversation(
                    conversation,
                    messages_ordered,
                )

            # 3. Load Workspace Context
            selected_documents = []
            if document_ids:
                for doc_id in document_ids:
                    doc = await self._storage_tool.load_document(
                        LoadDocumentRequest(document_id=doc_id, organization_id=organization_id)
                    )
                    if doc is None:
                        logger.warning(
                            "context_loading_validation_failed",
                            reason="document_not_found",
                            document_id=str(doc_id),
                        )
                        raise ResourceNotFoundException(
                            "Document not found",
                            details={"document_id": doc_id},
                        )
                    selected_documents.append(RuntimeContextBuilder.build_document(doc))

            workspace_context = WorkspaceContext(selected_documents=selected_documents)

            # 4. Load Execution Context
            execution_context = RuntimeContextBuilder.build_execution(
                query=query,
                top_k=top_k,
                document_ids=document_ids,
                settings=self._settings,
            )

            runtime_context = RuntimeContext(
                conversation=conversation_context,
                session=session_context,
                workspace=workspace_context,
                execution=execution_context,
            )

            sections = ["session"]
            if conversation_context:
                sections.append("conversation")
            if document_ids:
                sections.append("workspace")
            sections.append("execution")

            duration = perf_counter() - start_time
            logger.info(
                "context_loading_completed",
                user_id=str(user_id),
                organization_id=str(organization_id),
                loaded_sections=sections,
                duration_seconds=round(duration, 4),
            )
            return runtime_context

        except Exception as exception:
            duration = perf_counter() - start_time
            logger.error(
                "context_loading_failed",
                user_id=str(user_id),
                organization_id=str(organization_id),
                error=str(exception),
                duration_seconds=round(duration, 4),
            )
            raise
