import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.ingestion.embedder import generate_embeddings
from src.db.chunks import chunk_repository
from src.logger import get_logger

logger = get_logger(__name__)

TOP_K = 5


async def hybrid_search(
    query: str,
    client,  # kept for backward compatibility with agent nodes
    doc_types: list[str] | None = None,
    top_k: int = TOP_K,
    db: AsyncSession | None = None,
) -> list[dict]:
    """Hybrid BM25 + semantic search using pgvector and PostgreSQL full-text search.

    Combines keyword search (tsvector/tsquery) and vector similarity search
    using Reciprocal Rank Fusion to produce a single ranked list.

    Args:
        query: User's question in German or English.
        client: Unused — kept for backward compatibility.
        doc_types: Optional list of doc types to filter by.
        top_k: Number of results to return.
        db: Async database session.

    Returns:
        List of chunk dicts ranked by hybrid relevance score.
    """
    logger.info("hybrid_search_started", query=query, top_k=top_k)

    if db is None:
        raise ValueError("db session is required for pgvector hybrid search")

    # Generate query embedding
    query_embeddings = await generate_embeddings([query], task="retrieval.query")
    query_vector = query_embeddings[0]

    results = await chunk_repository.hybrid_search(
        db=db,
        query_text=query,
        query_embedding=query_vector,
        doc_types=doc_types,
        top_k=top_k,
    )

    logger.info("hybrid_search_completed", query=query, results_count=len(results))
    return results