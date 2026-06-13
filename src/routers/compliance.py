import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.postgres import get_db
from src.compliance.audit import audit_service
from src.compliance.chat import chat_service
from src.compliance.erasure import erasure_service
from src.dependencies import verify_api_key, get_request_id
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/compliance", tags=["compliance"])


class ErasureResponse(BaseModel):
    """Response after DSGVO erasure."""
    user_id: str
    audit_logs_deleted: int
    chat_sessions_deleted: int
    chat_messages_deleted: int
    documents_deleted: int
    erasure_timestamp: str


@router.get("/audit/{user_id}")
async def get_audit_trail(
    user_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full audit trail for a user.
    
    Returns all queries made by this user with chunks used
    and answers generated. DSGVO Article 15 — right of access.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("audit_trail_requested", user_id=user_id)

    logs = await audit_service.get_audit_trail(db, user_id)
    return {
        "user_id": user_id,
        "total_logs": len(logs),
        "logs": [
            {
                "id": log.id,
                "session_id": log.session_id,
                "query_text": log.query_text,
                "rewritten_query": log.rewritten_query,
                "answer": log.answer,
                "doc_ids": log.doc_ids,
                "chunk_ids": log.chunk_ids,
                "model_name": log.model_name,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/sessions/{user_id}")
async def get_user_sessions(
    user_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all chat sessions for a user."""
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    sessions = await chat_service.get_user_sessions(db, user_id)
    return {
        "user_id": user_id,
        "total_sessions": len(sessions),
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all messages in a chat session."""
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    messages = await chat_service.get_history_for_llm(db, session_id, max_turns=100)
    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "messages": messages,
    }


@router.delete("/users/{user_id}", response_model=ErasureResponse)
async def erase_user_data(
    user_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Erase all data for a user — DSGVO Article 17 right to erasure.
    
    Deletes from PostgreSQL atomically. Document chunks are removed
    automatically via foreign key cascade.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("erasure_requested", user_id=user_id)

    try:
        summary = await erasure_service.erase_user_data(
            db=db,
            user_id=user_id,
        )
        return ErasureResponse(**summary)
    except ValueError as e:
        logger.error("erasure_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))