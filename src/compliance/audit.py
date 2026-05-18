import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.db.models import AuditLog
from src.logger import get_logger

logger = get_logger(__name__)

class AuditRepository():
    "Data Access layer for Audit logs."
    async def create(self, db: AsyncSession, data:dict)-> AuditLog:
        "Write a new Audit log entry."
        log = AuditLog(
            id=str(uuid.uuid4()),
            session_id=data.get("session_id"),
            user_id=data["user_id"],
            query_text=data["query_text"],
            rewritten_query=data.get("rewritten_query",""),
            chunk_ids=data.get("chunk_ids",[]),
            doc_ids=data.get("doc_ids",[]),
            answer=data.get("answer",""),
            model_name=data.get("model_name",""),
            prompt_tokens=data.get("prompt_tokens",0),
            completion_tokens=data.get("completion_tokens",0),
            )
        db.add(log)
        await db.flush()
        logger.info(
            "audit_log_created",
            audit_id=log.id,
            user_id=log.user_id,
            query=log.query_text[:50],
        )
        return log
    
    async def get_by_user(
            self, db:AsyncSession, user_id:str
    )-> list[AuditLog]:
        "Retrieve all audit logs for an user."
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
        )
        return list(result.scalars().all())
    

class AuditService:
    """Business logic for audit logging.
    
    Single responsibility: enforce audit rules and coordinate
    between the HTTP layer and the repository.
    Depends on AuditRepository — never on SQLAlchemy directly.
    """

    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def log_query(
        self,
        db: AsyncSession,
        user_id: str,
        query_text: str,
        answer: str,
        chunks: list[dict],
        rewritten_query: str = "",
        session_id: str | None = None,
        model_name: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> AuditLog:
        """Log a complete query interaction for audit trail."""
        chunk_ids = [
            c.get("_id", c.get("chunk_index", i))
            for i, c in enumerate(chunks)
        ]
        doc_ids = list({c.get("doc_id", "") for c in chunks})

        return await self.repository.create(db, {
            "session_id": session_id,
            "user_id": user_id,
            "query_text": query_text,
            "rewritten_query": rewritten_query,
            "chunk_ids": chunk_ids,
            "doc_ids": doc_ids,
            "answer": answer,
            "model_name": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        })

    async def get_audit_trail(
        self, db: AsyncSession, user_id: str
    ) -> list[AuditLog]:
        """Retrieve full audit trail for a user."""
        return await self.repository.get_by_user(db, user_id)
    
# Module-level instances following dependency inversion
audit_repository = AuditRepository()
audit_service = AuditService(audit_repository)
