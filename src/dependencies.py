import uuid
import structlog
from functools import lru_cache
from fastapi import Header, HTTPException, Depends
from src.config import Settings, get_settings
from src.logger import get_logger

logger = get_logger(__name__)

@lru_cache
def get_cached_settings() -> Settings:
    """Cached settings - reads .env once and then serves from memory.
    
    Using lru_cache means the .env file is read exactly once at startup
    regardless of how many requests come in. Without this, every request
    would read and validate the .env file from disk.
    """
    return Settings()


async def verify_api_key(
        x_api_key: str = Header(default="")) -> str:
    """Verify the API on every protected environment.
    
    Reads the expected key from the Settings and compares with the x_api_key header. 
    Raises 401 if missing or invalid.

    Args:
        x_api_key: Value from x_api_key header.

    Returns:
        The validated API key string.

    Raises:
        HTTPException: 401 if key is missing or does not match.
    """
    settings = get_cached_settings()

    if not x_api_key:
        logger.warning("api_key_missing", path = "protected environment")

        raise HTTPException(
            status_code = 401,
            detail = "X API Key Header is required"
            )
    
    if x_api_key != settings.api_key:
        logger.warning("api_key_invalid", path = "protected environment")
        raise HTTPException(
            status_code = 401,
            detail = "Invalid API Key"
        )
    return x_api_key


def get_request_id()-> str:
    """Generate an unique request ID for tracing.
    
    This ID is bound to structlog context at the start of each request so
    every log line produced during that request includes it.

    Returns:
        A UUID4 string prefixed with 'req_'.
    """
    return f"req_{uuid.uuid4().hex[:12]}"