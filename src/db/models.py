from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class DocumentRecord(Base):
    """Postgres table for document metadata.
    
    Stores structured metadata about each document ingested.
    Content is stored here for audit purposes - OpenSearch stores chunks for search purposes.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)
    source_url = Column(String, default="")
    page_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    ingested_by = Column(String, default="system")
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """Audit trail for every query — DSGVO compliance."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    user_id = Column(String, nullable=False)
    query_text = Column(Text, nullable=False)
    rewritten_query = Column(Text, default="")
    chunk_ids = Column(JSON, default=list)
    doc_ids = Column(JSON, default=list)
    answer = Column(Text, default="")
    model_name = Column(String, default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    """A conversation session between a user and the system."""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    title = Column(String, default="")
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    """Individual message in a chat session."""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    query_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))