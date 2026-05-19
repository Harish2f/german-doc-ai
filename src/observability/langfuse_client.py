from langfuse import Langfuse, get_client, observe
from functools import lru_cache
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)


def init_langfuse() -> bool:
    """Initialise Langfuse from settings.
    
    Returns True if configured, False if keys missing.
    """
    settings = get_settings()

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("langfuse_not_configured")
        return False

    import os
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = settings.langfuse_host

    logger.info("langfuse_initialized")
    return True


def get_trace(name: str, user_id: str = "anonymous",  
              session_id: str | None = None,
              metadata: dict | None = None,
              tags: list[str] | None = None,):
    """Create a Langfuse trace with metadata for filtering."""
    try:
        client = get_client()
        return client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )
    except Exception:
        return None