import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import ChatSession, ChatMessage
from src.logger import get_logger

logger = get_logger(__name__)


class ChatRepository:
    """Data access layer for chat sessions and messages.
    
    Single responsibility: read and write chat tables only.
    """

    async def create_session(
        self, db: AsyncSession, user_id: str, title: str = ""
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
        )
        db.add(session)
        await db.flush()
        logger.info("chat_session_created", session_id=session.id, user_id=user_id)
        return session

    async def get_session(
        self, db: AsyncSession, session_id: str
    ) -> ChatSession | None:
        """Retrieve a chat session by ID."""
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self, db: AsyncSession, user_id: str
    ) -> list[ChatSession]:
        """Retrieve all sessions for a user."""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        query_id: str | None = None,
    ) -> ChatMessage:
        """Add a message to a chat session."""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            query_id=query_id,
        )
        db.add(message)
        await db.flush()
        return message

    async def get_messages(
        self, db: AsyncSession, session_id: str
    ) -> list[ChatMessage]:
        """Retrieve all messages for a session ordered chronologically."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())


class ChatService:
    """Business logic for chat history management.
    
    Single responsibility: manage conversation flow and
    format history for GPT-4o consumption.
    """

    def __init__(self, repository: ChatRepository):
        self.repository = repository

    async def get_or_create_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str | None = None,
        first_message: str = "",
    ) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id:
            session = await self.repository.get_session(db, session_id)
            if session:
                return session

        title = first_message[:50] if first_message else "New conversation"
        return await self.repository.create_session(db, user_id, title)

    async def add_turn(
        self,
        db: AsyncSession,
        session_id: str,
        user_message: str,
        assistant_message: str,
        query_id: str | None = None,
    ) -> tuple[ChatMessage, ChatMessage]:
        """Add a complete conversation turn — user message and assistant response."""
        user_msg = await self.repository.add_message(
            db, session_id, "user", user_message, query_id
        )
        assistant_msg = await self.repository.add_message(
            db, session_id, "assistant", assistant_message, query_id
        )
        return user_msg, assistant_msg

    async def get_history_for_llm(
        self, db: AsyncSession, session_id: str, max_turns: int = 10
    ) -> list[dict]:
        """Retrieve conversation history formatted for GPT-4o.
        
        Limits to last max_turns to avoid exceeding context window.
        
        Returns:
            List of role/content dicts ready for OpenAI messages array.
        """
        messages = await self.repository.get_messages(db, session_id)
        recent = messages[-(max_turns * 2):]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent
        ]

    async def get_user_sessions(
        self, db: AsyncSession, user_id: str
    ) -> list[ChatSession]:
        """Retrieve all sessions for a user."""
        return await self.repository.get_user_sessions(db, user_id)


# Module-level instances
chat_repository = ChatRepository()
chat_service = ChatService(chat_repository)