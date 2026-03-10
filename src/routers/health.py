from fastapi import APIRouter
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """Check if the service is running.
    
    Returns basic service status. No authentication required —
    used by Azure Container Apps to verify the container is healthy.
    """
    logger.info("health_check_called")
    return {
        "status" : "ok",
        "service" : "GermanDocAI"
    }