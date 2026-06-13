import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.db.models import AuditLog, ChatMessage, ChatSession, DocumentRecord
from src.logger import get_logger

logger = get_logger(__name__)


class ErasureRepository:
    """Data access layer for DSGVO right-to-erasure operations.
    
    Single responsibility: delete user data across all tables.
    Document chunks are deleted automatically via ON DELETE CASCADE
    when the parent document is deleted.
    """

    async def delete_audit_logs(
        self, db: AsyncSession, user_id: str
    ) -> int:
        result = await db.execute(
            delete(AuditLog).where(AuditLog.user_id == user_id)
        )
        return result.rowcount

    async def delete_chat_messages_by_sessions(
        self, db: AsyncSession, session_ids: list[str]
    ) -> int:
        if not session_ids:
            return 0
        result = await db.execute(
            delete(ChatMessage).where(
                ChatMessage.session_id.in_(session_ids)
            )
        )
        return result.rowcount

    async def delete_chat_sessions(
        self, db: AsyncSession, user_id: str
    ) -> list[str]:
        """Delete sessions and return their IDs for message deletion."""
        result = await db.execute(
            select(ChatSession.id).where(ChatSession.user_id == user_id)
        )
        session_ids = list(result.scalars().all())
        await db.execute(
            delete(ChatSession).where(ChatSession.user_id == user_id)
        )
        return session_ids

    async def get_user_doc_ids(
        self, db: AsyncSession, user_id: str
    ) -> list[str]:
        """Get IDs of documents ingested by this user."""
        result = await db.execute(
            select(DocumentRecord.id).where(
                DocumentRecord.ingested_by == user_id
            )
        )
        return list(result.scalars().all())

    async def delete_user_documents(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """Delete user documents. Chunks are removed automatically via CASCADE."""
        result = await db.execute(
            delete(DocumentRecord).where(
                DocumentRecord.ingested_by == user_id
            )
        )
        return result.rowcount


class ErasureService:
    """Orchestrates complete DSGVO user data erasure.
    
    Single responsibility: coordinate deletion across all PostgreSQL
    tables. Document chunks cascade-delete with their parent documents,
    so a single PostgreSQL transaction handles complete erasure.
    """

    def __init__(self, repository: ErasureRepository):
        self.repository = repository

    async def erase_user_data(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> dict:
        """Erase all data for a user — DSGVO Article 17.
        
        Args:
            db: Async database session.
            user_id: User whose data to erase.
            
        Returns:
            Summary of what was deleted.
        """
        logger.info("erasure_started", user_id=user_id)

        # Document chunks cascade-delete automatically via ON DELETE CASCADE
        session_ids = await self.repository.delete_chat_sessions(db, user_id)
        messages_deleted = await self.repository.delete_chat_messages_by_sessions(
            db, session_ids
        )
        audit_logs_deleted = await self.repository.delete_audit_logs(db, user_id)
        docs_deleted = await self.repository.delete_user_documents(db, user_id)

        summary = {
            "user_id": user_id,
            "audit_logs_deleted": audit_logs_deleted,
            "chat_sessions_deleted": len(session_ids),
            "chat_messages_deleted": messages_deleted,
            "documents_deleted": docs_deleted,
            "erasure_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("erasure_completed", **summary)
        return summary


# Module-level instances
erasure_repository = ErasureRepository()
erasure_service = ErasureService(erasure_repository)