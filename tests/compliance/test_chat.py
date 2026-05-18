import pytest
from sqlalchemy import select

from src.db.models import ChatSession, ChatMessage
from src.compliance.chat import (
    ChatRepository,
    ChatService,
)


@pytest.mark.asyncio
async def test_create_session_persists_chat_session(db_session):
    """Test repository creates and persists a chat session."""

    repository = ChatRepository()

    session = await repository.create_session(
        db=db_session,
        user_id="user-123",
        title="ML Discussion",
    )

    await db_session.commit()

    result = await db_session.execute(
        select(ChatSession).where(ChatSession.id == session.id)
    )

    saved_session = result.scalar_one()

    assert saved_session.id == session.id
    assert saved_session.user_id == "user-123"
    assert saved_session.title == "ML Discussion"


@pytest.mark.asyncio
async def test_get_session_returns_existing_session(db_session):
    """Test repository fetches session by ID."""

    repository = ChatRepository()

    created = await repository.create_session(
        db=db_session,
        user_id="user-1",
        title="Test Session",
    )

    await db_session.commit()

    fetched = await repository.get_session(
        db=db_session,
        session_id=created.id,
    )

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.user_id == "user-1"


@pytest.mark.asyncio
async def test_get_session_returns_none_for_invalid_id(db_session):
    """Test repository returns None for missing session."""

    repository = ChatRepository()

    session = await repository.get_session(
        db=db_session,
        session_id="invalid-session-id",
    )

    assert session is None


@pytest.mark.asyncio
async def test_get_user_sessions_filters_by_user(db_session):
    """Test repository returns only sessions belonging to user."""

    repository = ChatRepository()

    await repository.create_session(
        db_session,
        user_id="user-a",
        title="Session A",
    )

    await repository.create_session(
        db_session,
        user_id="user-b",
        title="Session B",
    )

    await repository.create_session(
        db_session,
        user_id="user-a",
        title="Session C",
    )

    await db_session.commit()

    sessions = await repository.get_user_sessions(
        db_session,
        "user-a",
    )

    assert len(sessions) == 2

    titles = [s.title for s in sessions]

    assert "Session A" in titles
    assert "Session C" in titles
    assert "Session B" not in titles


@pytest.mark.asyncio
async def test_add_message_persists_chat_message(db_session):
    """Test repository stores chat message correctly."""

    repository = ChatRepository()

    session = await repository.create_session(
        db_session,
        user_id="user-123",
    )

    message = await repository.add_message(
        db=db_session,
        session_id=session.id,
        role="user",
        content="What is LangChain?",
        query_id="query-1",
    )

    await db_session.commit()

    result = await db_session.execute(
        select(ChatMessage).where(ChatMessage.id == message.id)
    )

    saved_message = result.scalar_one()

    assert saved_message.session_id == session.id
    assert saved_message.role == "user"
    assert saved_message.content == "What is LangChain?"
    assert saved_message.query_id == "query-1"


@pytest.mark.asyncio
async def test_get_messages_returns_messages_in_order(db_session):
    """Test repository returns chronological message order."""

    repository = ChatRepository()

    session = await repository.create_session(
        db_session,
        user_id="user-1",
    )

    await repository.add_message(
        db_session,
        session.id,
        "user",
        "First message",
    )

    await repository.add_message(
        db_session,
        session.id,
        "assistant",
        "Second message",
    )

    await db_session.commit()

    messages = await repository.get_messages(
        db_session,
        session.id,
    )

    assert len(messages) == 2
    assert messages[0].content == "First message"
    assert messages[1].content == "Second message"


@pytest.mark.asyncio
async def test_get_or_create_session_returns_existing_session(db_session):
    """Test service reuses existing session."""

    repository = ChatRepository()
    service = ChatService(repository)

    existing = await repository.create_session(
        db_session,
        user_id="user-123",
        title="Existing Session",
    )

    await db_session.commit()

    result = await service.get_or_create_session(
        db=db_session,
        user_id="user-123",
        session_id=existing.id,
    )

    assert result.id == existing.id
    assert result.title == "Existing Session"


@pytest.mark.asyncio
async def test_get_or_create_session_creates_new_session(db_session):
    """Test service creates session when session_id is missing."""

    repository = ChatRepository()
    service = ChatService(repository)

    session = await service.get_or_create_session(
        db=db_session,
        user_id="user-new",
        first_message="Explain vector databases in detail",
    )

    await db_session.commit()

    assert session.user_id == "user-new"
    assert session.title == "Explain vector databases in detail"


@pytest.mark.asyncio
async def test_get_or_create_session_uses_default_title(db_session):
    """Test service uses fallback title when no first message exists."""

    repository = ChatRepository()
    service = ChatService(repository)

    session = await service.get_or_create_session(
        db=db_session,
        user_id="user-empty",
    )

    await db_session.commit()

    assert session.title == "New conversation"


@pytest.mark.asyncio
async def test_add_turn_creates_user_and_assistant_messages(db_session):
    """Test service creates complete conversation turn."""

    repository = ChatRepository()
    service = ChatService(repository)

    session = await repository.create_session(
        db_session,
        user_id="user-chat",
    )

    user_msg, assistant_msg = await service.add_turn(
        db=db_session,
        session_id=session.id,
        user_message="What is RAG?",
        assistant_message="RAG combines retrieval and generation.",
        query_id="query-xyz",
    )

    await db_session.commit()

    assert user_msg.role == "user"
    assert user_msg.content == "What is RAG?"

    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == (
        "RAG combines retrieval and generation."
    )

    assert user_msg.query_id == "query-xyz"
    assert assistant_msg.query_id == "query-xyz"


@pytest.mark.asyncio
async def test_get_history_for_llm_formats_messages_correctly(db_session):
    """Test service formats history for OpenAI message structure."""

    repository = ChatRepository()
    service = ChatService(repository)

    session = await repository.create_session(
        db_session,
        user_id="user-llm",
    )

    await repository.add_message(
        db_session,
        session.id,
        "user",
        "Hello",
    )

    await repository.add_message(
        db_session,
        session.id,
        "assistant",
        "Hi there",
    )

    await db_session.commit()

    history = await service.get_history_for_llm(
        db=db_session,
        session_id=session.id,
    )

    assert history == [
        {
            "role": "user",
            "content": "Hello",
        },
        {
            "role": "assistant",
            "content": "Hi there",
        },
    ]


@pytest.mark.asyncio
async def test_get_history_for_llm_limits_max_turns(db_session):
    """Test service truncates history to max_turns."""

    repository = ChatRepository()
    service = ChatService(repository)

    session = await repository.create_session(
        db_session,
        user_id="truncate-user",
    )

    for i in range(15):
        await repository.add_message(
            db_session,
            session.id,
            "user",
            f"user-{i}",
        )

        await repository.add_message(
            db_session,
            session.id,
            "assistant",
            f"assistant-{i}",
        )

    await db_session.commit()

    history = await service.get_history_for_llm(
        db=db_session,
        session_id=session.id,
        max_turns=5,
    )

    assert len(history) == 10

    assert history[0]["content"] == "user-10"
    assert history[-1]["content"] == "assistant-14"


@pytest.mark.asyncio
async def test_service_get_user_sessions_returns_user_sessions(db_session):
    """Test service delegates user session retrieval."""

    repository = ChatRepository()
    service = ChatService(repository)

    await repository.create_session(
        db_session,
        user_id="service-user",
        title="Session 1",
    )

    await repository.create_session(
        db_session,
        user_id="service-user",
        title="Session 2",
    )

    await repository.create_session(
        db_session,
        user_id="other-user",
        title="Other Session",
    )

    await db_session.commit()

    sessions = await service.get_user_sessions(
        db_session,
        "service-user",
    )

    assert len(sessions) == 2

    titles = [s.title for s in sessions]

    assert "Session 1" in titles
    assert "Session 2" in titles
    assert "Other Session" not in titles