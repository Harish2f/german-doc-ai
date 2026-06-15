import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.ingestion.embedder import generate_embeddings
from src.db.chunks import chunk_repository
from src.logger import get_logger
from src.search.reranker import rerank_chunks

logger = get_logger(__name__)

TOP_K = 5

async def hybrid_search(
    query: str,
    client,
    doc_types: list[str] | None = None,
    top_k: int = 5,
    db: AsyncSession | None = None,
) -> list[dict]:
    logger.info("hybrid_search_started", query=query, top_k=top_k)

    if db is None:
        raise ValueError("db session is required for pgvector hybrid search")

    query_embeddings = await generate_embeddings([query], task="retrieval.query")
    query_vector = query_embeddings[0]

    # Retrieve more candidates for reranking
    candidates = await chunk_repository.hybrid_search(
        db=db,
        query_text=query,
        query_embedding=query_vector,
        doc_types=doc_types,
        top_k=top_k * 3,  # retrieve 3x more for reranking
    )

    if not candidates:
        return []

    # Rerank with Cohere
    reranked = await rerank_chunks(
        query=query,
        chunks=candidates,
        top_k=top_k,
    )

    logger.info("hybrid_search_completed", query=query, results_count=len(reranked))
    return reranked