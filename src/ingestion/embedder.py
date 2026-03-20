import httpx
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v3"
EMBEDDING_DIMENSION=768

async def generate_embeddings(texts:list[str],
                              task: str= "retrieval.passage")-> list[list[float]]:
    """Generate Embeddings for a list of texts using JINA API.
    
    Args:
        texts: list of text strings to embed.

    Returns:
        List of 768 dimension vectors, one per input text.

    Raises:
        ValueError: If the API call fails or returns unexpected results.
    """
    settings = get_settings()

    if not texts:
        return []
    
    if not settings.jina_api_key:
        raise ValueError(
            "JINA_API_KEY is not set. "
            "Get a free key at https://jina.ai"
        )
    
    logger.info("generating_embeddings",batch_size=len(texts))

    async with httpx.AsyncClient() as client:
        response = await client.post(
            JINA_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {settings.jina_api_key}",
                "Content-Type": "application/json",
            },
            json = {
                "model":JINA_MODEL,
                "task":"retrieval.passage",
                "dimensions":EMBEDDING_DIMENSION,
                "input":texts,
            },
            timeout=60.0,
        )

        if response.status_code != 200:
            logger.error(
                "embedding_api_failed",
                status_code=response.status_code,
                response=response.text,
                )
            raise ValueError(
                f"JINA API returned {response.status_code}: {response.text}"
            )
        data = response.json()
        embeddings = [item["embedding"]for item in data["data"]]

        logger.info(
            "embeddings_generated",
            batch_size = len(texts),
            embedding_dimension = len(embeddings[0])if embeddings else 0,
        )

        return embeddings
    