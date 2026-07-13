"""Builder coordinating mapping of domain entities and configurations to RuntimeContext schemas."""

from uuid import UUID

from src.core.appEnvironment import AppEnvironment
from src.models.conversationModel import Conversation
from src.models.documentModel import Document
from src.models.messageModel import Message
from src.models.organizationModel import Organization
from src.models.userModel import User
from src.runtimeContext.runtimeContext import (
    ContextDocument,
    ContextMessage,
    ConversationContext,
    ExecutionContext,
    SessionContext,
)


class RuntimeContextBuilder:
    """Assembles domain models and configurations into clean, context-safe schemas."""

    @staticmethod
    def build_message(msg: Message) -> ContextMessage:
        """Map message ORM row representation to ContextMessage schema."""
        return ContextMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            citations=msg.citations,
            created_at=msg.created_at,
        )

    @staticmethod
    def build_conversation(conv: Conversation, messages: list[Message]) -> ConversationContext:
        """Map conversation metadata and message turn list to ConversationContext."""
        return ConversationContext(
            conversation_id=conv.id,
            title=conv.title,
            recent_messages=[RuntimeContextBuilder.build_message(m) for m in messages],
        )

    @staticmethod
    def build_document(doc: Document) -> ContextDocument:
        """Map document ORM row representation to ContextDocument metadata schema."""
        return ContextDocument(
            id=doc.id,
            original_file_name=doc.original_file_name,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            upload_status=doc.upload_status,
            parsing_status=doc.parsing_status,
            embedding_status=doc.embedding_status,
            created_at=doc.created_at,
        )

    @staticmethod
    def build_session(org: Organization, user: User) -> SessionContext:
        """Map organization and user details along with roles to SessionContext."""
        role_names = [role.role_name for role in user.roles] if user.roles else []
        return SessionContext(
            organization_id=org.id,
            organization_name=org.organization_name,
            user_id=user.id,
            email_address=user.email_address,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=role_names,
        )

    @staticmethod
    def build_execution(
        *,
        query: str,
        top_k: int,
        document_ids: list[UUID] | None,
        settings: AppEnvironment,
    ) -> ExecutionContext:
        """Map runtime parameters and config settings to ExecutionContext."""
        return ExecutionContext(
            query=query,
            top_k=top_k,
            document_ids=document_ids,
            enable_original_file_storage=settings.enable_original_file_storage,
            hybrid_retrieval_enabled=settings.hybrid_retrieval_enabled,
            active_llm_provider=settings.active_llm_provider,
            embedding_model=settings.resolved_embedding_model,
            chat_history_max_messages=settings.chat_history_max_messages,
        )
