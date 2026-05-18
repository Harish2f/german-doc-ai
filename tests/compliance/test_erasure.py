from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.db.models import (
    AuditLog,
    ChatMessage,
    ChatSession,
    DocumentRecord,
)
from src.compliance.erasure import (
    ErasureRepository,
    ErasureService,
)


@pytest.mark.asyncio
async def test_delete_audit_logs_removes_user_logs(db_session):
    """Test repository deletes only matching user audit logs."""

    repository = ErasureRepository()

    db_session.add_all(
        [
            AuditLog(
                id="audit-1",
                user_id="user-1",
                query_text="query-1",
            ),
            AuditLog(
                id="audit-2",
                user_id="user-1",
                query_text="query-2",
            ),
            AuditLog(
                id="audit-3",
                user_id="user-2",
                query_text="query-3",
            ),
        ]
    )

    await db_session.commit()

    deleted_count = await repository.delete_audit_logs(
        db_session,
        "user-1",
    )

    await db_session.commit()

    remaining = await db_session.execute(select(AuditLog))

    logs = remaining.scalars().all()

    assert deleted_count == 2
    assert len(logs) == 1
    assert logs[0].user_id == "user-2"


@pytest.mark.asyncio
async def test_delete_chat_messages_by_sessions(db_session):
    """Test repository deletes messages for specified sessions."""

    repository = ErasureRepository()

    session_1 = ChatSession(
        id="session-1",
        user_id="user-1",
    )

    session_2 = ChatSession(
        id="session-2",
        user_id="user-2",
    )

    db_session.add_all([session_1, session_2])

    db_session.add_all(
        [
            ChatMessage(
                id="msg-1",
                session_id="session-1",
                role="user",
                content="hello",
            ),
            ChatMessage(
                id="msg-2",
                session_id="session-1",
                role="assistant",
                content="hi",
            ),
            ChatMessage(
                id="msg-3",
                session_id="session-2",
                role="user",
                content="other",
            ),
        ]
    )

    await db_session.commit()

    deleted = await repository.delete_chat_messages_by_sessions(
        db_session,
        ["session-1"],
    )

    await db_session.commit()

    result = await db_session.execute(select(ChatMessage))

    remaining = result.scalars().all()

    assert deleted == 2
    assert len(remaining) == 1
    assert remaining[0].session_id == "session-2"


@pytest.mark.asyncio
async def test_delete_chat_messages_handles_empty_session_ids(db_session):
    """Test repository safely handles empty session list."""

    repository = ErasureRepository()

    deleted = await repository.delete_chat_messages_by_sessions(
        db_session,
        [],
    )

    assert deleted == 0


@pytest.mark.asyncio
async def test_delete_chat_sessions_returns_deleted_session_ids(db_session):
    """Test repository returns deleted session IDs."""

    repository = ErasureRepository()

    db_session.add_all(
        [
            ChatSession(
                id="session-a",
                user_id="user-1",
            ),
            ChatSession(
                id="session-b",
                user_id="user-1",
            ),
            ChatSession(
                id="session-c",
                user_id="user-2",
            ),
        ]
    )

    await db_session.commit()

    session_ids = await repository.delete_chat_sessions(
        db_session,
        "user-1",
    )

    await db_session.commit()

    result = await db_session.execute(select(ChatSession))

    remaining = result.scalars().all()

    assert set(session_ids) == {"session-a", "session-b"}

    assert len(remaining) == 1
    assert remaining[0].user_id == "user-2"


@pytest.mark.asyncio
async def test_get_user_doc_ids_returns_matching_documents(db_session):
    """Test repository returns only user's document IDs."""

    repository = ErasureRepository()

    db_session.add_all(
        [
            DocumentRecord(
                id="doc-1",
                title="Test Document",
                doc_type="bafin",
                ingested_by="user-1",
            ),
            DocumentRecord(
                id="doc-2",
                title="Test Document",
                doc_type="bafin",
                ingested_by="user-1",
            ),
            DocumentRecord(
                id="doc-3",
                title="Test Document",
                doc_type="bafin",
                ingested_by="user-2",
            ),
        ]
    )

    await db_session.commit()

    doc_ids = await repository.get_user_doc_ids(
        db_session,
        "user-1",
    )

    assert set(doc_ids) == {"doc-1", "doc-2"}


@pytest.mark.asyncio
async def test_delete_user_documents_removes_matching_docs(db_session):
    """Test repository deletes only matching user documents."""

    repository = ErasureRepository()

    db_session.add_all(
        [
            DocumentRecord(
                id="doc-1",
                title="Test Document",
                doc_type="bafin",
                ingested_by="user-1",
            ),
            DocumentRecord(
                id="doc-2",
                title="Test Document",
                doc_type="bafin",
                ingested_by="user-1",
            ),
            DocumentRecord(
                id="doc-3",
                title="Test Document",
                doc_type="bafin",
                ingested_by="user-2",
            ),
        ]
    )

    await db_session.commit()

    deleted = await repository.delete_user_documents(
        db_session,
        "user-1",
    )

    await db_session.commit()

    result = await db_session.execute(select(DocumentRecord))

    remaining = result.scalars().all()

    assert deleted == 2
    assert len(remaining) == 1
    assert remaining[0].ingested_by == "user-2"


@pytest.mark.asyncio
async def test_erase_user_data_successfully_removes_everything(db_session):
    """Test service fully erases user data across systems."""

    repository = ErasureRepository()
    service = ErasureService(repository)

    session = ChatSession(
        id="session-1",
        user_id="target-user",
    )

    db_session.add(session)

    db_session.add_all(
        [
            ChatMessage(
                id="msg-1",
                session_id="session-1",
                role="user",
                content="hello",
            ),
            AuditLog(
                id="audit-1",
                user_id="target-user",
                query_text="query",
            ),
            DocumentRecord(
                id="doc-1",
                ingested_by="target-user",
                title="Test Document",
                doc_type="bafin",
            ),
        ]
    )

    await db_session.commit()

    mock_opensearch = AsyncMock()

    mock_opensearch.delete_by_query.return_value = {
        "deleted": 7
    }

    mock_opensearch.count.return_value = {
        "count": 0
    }

    summary = await service.erase_user_data(
        db=db_session,
        opensearch_client=mock_opensearch,
        user_id="target-user",
    )

    await db_session.commit()

    remaining_sessions = await db_session.execute(
        select(ChatSession)
    )

    remaining_messages = await db_session.execute(
        select(ChatMessage)
    )

    remaining_audits = await db_session.execute(
        select(AuditLog)
    )

    remaining_docs = await db_session.execute(
        select(DocumentRecord)
    )

    assert remaining_sessions.scalars().all() == []
    assert remaining_messages.scalars().all() == []
    assert remaining_audits.scalars().all() == []
    assert remaining_docs.scalars().all() == []

    assert summary["user_id"] == "target-user"
    assert summary["audit_logs_deleted"] == 1
    assert summary["chat_sessions_deleted"] == 1
    assert summary["chat_messages_deleted"] == 1
    assert summary["documents_deleted"] == 1
    assert summary["opensearch_chunks_deleted"] == 7

    mock_opensearch.delete_by_query.assert_awaited_once()
    mock_opensearch.count.assert_awaited_once()


@pytest.mark.asyncio
async def test_erase_user_data_aborts_when_opensearch_incomplete(
    db_session,
):
    """Test service aborts PostgreSQL deletion if OpenSearch fails."""

    repository = ErasureRepository()
    service = ErasureService(repository)

    db_session.add(
        DocumentRecord(
            id="doc-1",
            ingested_by="target-user",
            title="Test Document",
            doc_type="bafin",
        )
    )

    db_session.add(
        AuditLog(
            id="audit-1",
            user_id="target-user",
            query_text="query",
        )
    )

    await db_session.commit()

    mock_opensearch = AsyncMock()

    mock_opensearch.delete_by_query.return_value = {
        "deleted": 1
    }

    mock_opensearch.count.return_value = {
        "count": 2
    }

    with pytest.raises(ValueError) as exc:
        await service.erase_user_data(
            db=db_session,
            opensearch_client=mock_opensearch,
            user_id="target-user",
        )

    assert "OpenSearch erasure incomplete" in str(exc.value)

    result = await db_session.execute(select(AuditLog))

    remaining_logs = result.scalars().all()

    assert len(remaining_logs) == 1


@pytest.mark.asyncio
async def test_erase_user_data_skips_opensearch_when_no_documents(
    db_session,
):
    """Test service skips OpenSearch calls if user has no documents."""

    repository = ErasureRepository()
    service = ErasureService(repository)

    db_session.add(
        AuditLog(
            id="audit-1",
            user_id="user-no-docs",
            query_text="query",
        )
    )

    await db_session.commit()

    mock_opensearch = AsyncMock()

    summary = await service.erase_user_data(
        db=db_session,
        opensearch_client=mock_opensearch,
        user_id="user-no-docs",
    )

    await db_session.commit()

    assert summary["audit_logs_deleted"] == 1
    assert summary["documents_deleted"] == 0
    assert summary["opensearch_chunks_deleted"] == 0

    mock_opensearch.delete_by_query.assert_not_called()
    mock_opensearch.count.assert_not_called()