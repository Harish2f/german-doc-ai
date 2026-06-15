import cohere
import os
from src.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)

_cohere_client = None


def get_cohere_client() -> cohere.Client:
    global _cohere_client
    if _cohere_client is None:
        settings = get_settings()
        if not settings.cohere_api_key:
            raise ValueError("COHERE_API_KEY not set")
        _cohere_client = cohere.Client(settings.cohere_api_key)
    return _cohere_client


async def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Rerank chunks using Cohere reranker.
    
    Takes initial hybrid search results and reranks them
    using a cross-encoder model for better relevance.
    
    Args:
        query: User query.
        chunks: List of chunk dicts from hybrid search.
        top_k: Number of top chunks to return after reranking.
        
    Returns:
        Reranked list of chunk dicts.
    """
    if not chunks:
        return chunks

    try:
        client = get_cohere_client()
        documents = [chunk["text"] for chunk in chunks]

        response = client.rerank(
            model="rerank-v3.5",
            query=query,
            documents=documents,
            top_n=top_k,
        )

        reranked = []
        for result in response.results:
            chunk = chunks[result.index].copy()
            chunk["rerank_score"] = result.relevance_score
            reranked.append(chunk)

        logger.info(
            "chunks_reranked",
            query=query,
            original_count=len(chunks),
            reranked_count=len(reranked),
        )
        return reranked

    except Exception as e:
        logger.warning("reranking_failed", error=str(e))
        return chunks[:top_k]