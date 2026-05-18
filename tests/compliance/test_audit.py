import pytest
import pytest_asyncio
from sqlalchemy import select

from src.db.models import AuditLog
from src.compliance.audit import (
    AuditRepository,
    AuditService,
)


@pytest.mark.asyncio
async def test_create_audit_log(db_session):
    """Test repository create persists an audit log."""

    repository = AuditRepository()

    payload = {
        "session_id": "session-123",
        "user_id": "user-1",
        "query_text": "What is RAG?",
        "rewritten_query": "Explain retrieval augmented generation",
        "chunk_ids": ["chunk-1", "chunk-2"],
        "doc_ids": ["doc-1"],
        "answer": "RAG combines retrieval and generation.",
        "model_name": "gpt-4",
        "prompt_tokens": 120,
        "completion_tokens": 45,
    }

    log = await repository.create(db_session, payload)

    await db_session.commit()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.id == log.id)
    )

    saved_log = result.scalar_one()

    assert saved_log.id == log.id
    assert saved_log.user_id == "user-1"
    assert saved_log.query_text == "What is RAG?"
    assert saved_log.rewritten_query == (
        "Explain retrieval augmented generation"
    )
    assert saved_log.chunk_ids == ["chunk-1", "chunk-2"]
    assert saved_log.doc_ids == ["doc-1"]
    assert saved_log.answer == "RAG combines retrieval and generation."
    assert saved_log.model_name == "gpt-4"
    assert saved_log.prompt_tokens == 120
    assert saved_log.completion_tokens == 45


@pytest.mark.asyncio
async def test_get_by_user_returns_only_matching_user_logs(db_session):
    """Test repository filters audit logs by user."""

    repository = AuditRepository()

    await repository.create(
        db_session,
        {
            "user_id": "user-a",
            "query_text": "Query A",
        },
    )

    await repository.create(
        db_session,
        {
            "user_id": "user-b",
            "query_text": "Query B",
        },
    )

    await db_session.commit()

    logs = await repository.get_by_user(db_session, "user-a")

    assert len(logs) == 1
    assert logs[0].user_id == "user-a"
    assert logs[0].query_text == "Query A"


@pytest.mark.asyncio
async def test_service_log_query_builds_chunk_and_doc_ids(db_session):
    """Test service derives chunk_ids and doc_ids correctly."""

    repository = AuditRepository()
    service = AuditService(repository)

    chunks = [
        {
            "_id": "chunk-101",
            "doc_id": "doc-1",
            "text": "Chunk 1",
        },
        {
            "_id": "chunk-102",
            "doc_id": "doc-2",
            "text": "Chunk 2",
        },
        {
            "_id": "chunk-103",
            "doc_id": "doc-1",
            "text": "Chunk 3",
        },
    ]

    log = await service.log_query(
        db=db_session,
        user_id="user-123",
        query_text="Explain transformers",
        answer="Transformers are attention-based models.",
        chunks=chunks,
        rewritten_query="What are transformer models?",
        session_id="session-xyz",
        model_name="gpt-4o",
        prompt_tokens=200,
        completion_tokens=80,
    )

    await db_session.commit()

    assert log.user_id == "user-123"
    assert log.chunk_ids == [
        "chunk-101",
        "chunk-102",
        "chunk-103",
    ]

    assert set(log.doc_ids) == {"doc-1", "doc-2"}

    assert log.rewritten_query == (
        "What are transformer models?"
    )

    assert log.model_name == "gpt-4o"
    assert log.prompt_tokens == 200
    assert log.completion_tokens == 80


@pytest.mark.asyncio
async def test_service_handles_empty_chunks(db_session):
    """Test service handles empty chunk list safely."""

    repository = AuditRepository()
    service = AuditService(repository)

    log = await service.log_query(
        db=db_session,
        user_id="user-empty",
        query_text="Hello",
        answer="Hi",
        chunks=[],
    )

    await db_session.commit()

    assert log.chunk_ids == []
    assert log.doc_ids == []


@pytest.mark.asyncio
async def test_get_audit_trail_returns_user_logs(db_session):
    """Test service returns audit trail for a user."""

    repository = AuditRepository()
    service = AuditService(repository)

    await service.log_query(
        db=db_session,
        user_id="user-trail",
        query_text="Question 1",
        answer="Answer 1",
        chunks=[],
    )

    await service.log_query(
        db=db_session,
        user_id="user-trail",
        query_text="Question 2",
        answer="Answer 2",
        chunks=[],
    )

    await service.log_query(
        db=db_session,
        user_id="another-user",
        query_text="Other question",
        answer="Other answer",
        chunks=[],
    )

    await db_session.commit()

    logs = await service.get_audit_trail(
        db_session,
        "user-trail",
    )

    assert len(logs) == 2

    queries = [log.query_text for log in logs]

    assert "Question 1" in queries
    assert "Question 2" in queries
    assert "Other question" not in queries