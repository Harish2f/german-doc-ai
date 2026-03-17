from opensearchpy import AsyncOpenSearch
from src.ingestion.embedder import generate_embeddings
from src.logger import get_logger

logger=get_logger(__name__)

INDEX_NAME = "german-docs-chunks"
TOP_K = 5

async def hybrid_search(
        query: str,
        client: AsyncOpenSearch,
        doc_types:list[str] | None = None,
        top_k: int = TOP_K,
) -> list[dict]:
    """Performance hybrid BM25 + Semantic Search on document chunks.
    
    Combines keyword search (BM25) AND Vector similarity search
    using reciprocal fusion rank to produce a single ranked list.

    Args:
        query: User's question in German or English.
        client: Async Opensearch client.
        doc_types: Optional list of doc types to filter by.
        top_k: Number of rewults to return.

    Returns:
        List of chunks dicts ranked by hybrid relevance score.
    """
    logger.info(
        "hybrid_search_started",
        query=query,
        top_k=top_k
    )

    # generate query embedding with retrieval.query task
    query_embeddings = await generate_embeddings([query])
    query_vector = query_embeddings[0]

    # Build Filter if doc_types is provided
    filter_clause = []
    if doc_types:
        filter_cause = [{"terms": {"doc_type": doc_types}}]

    # BM25 Keyword Search
    bm25_query = {
        "size": top_k * 2,
        "query": {
            "bool":{
                "must": [{"match": {"text": query}}],
                "filter": filter_clause,
            }
        },
    }

    # SEMANTIC VECTOR SEARCH

    knn_query = {
        "size": top_k * 2,
        "query": {
            "knn":{
                "embedding":{
                    "vector":query_vector,
                    "k": top_k * 2,
                }
            }
        },
    }

    # Run both searches concurrently
    import asyncio
    bm25_results, knn_results = await asyncio.gather(
        client.search(index=INDEX_NAME, body=bm25_query),
        client.search(index=INDEX_NAME, body=knn_query),
    )

    # Reciprocal rank fusion
    fused = reciprocal_rank_fusion(
        bm25_results["hits"]["hits"],
        knn_results["hits"]["hits"],
        top_k=top_k,
    )

    logger.info(
        "hybrid_search_completed",
        query = query,
        results_count = len(fused),
        )
    return fused

def reciprocal_rank_fusion(
        bm25_hits: list[dict],
        knn_hits:list[dict],
        top_k:int=TOP_K,
        k: int=60,
)-> list[dict]:
    """Combine BM25 and KNN results using reciprocal rank fusion.
    
    RRF Score = 1/(k + rank_in_bm25) + 1/(k + rank_in_knn)

    Higher Score = more relevant. Documents appearing high in
    both result lists get the highest combined scores.

    Args:
        bm25_hits: Results are BM25 keyword search.
        knn_hits: Results from KNN semantic search.
        top_k: Number of results o return.
        K: RRF constant - higher k reduces impact of rank differences.

    Returns:
        Top-k chunks sorted by RRF score descending.  
    """
    scores: dict[str, float]={}
    docs: dict[str, dict] = {}

    for rank, hit in enumerate(bm25_hits):
        doc_id=hit["_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1/ (k + rank + 1)
        docs[doc_id] = hit["_source"]

    for rank, hit in enumerate(knn_hits):
        doc_id = hit["_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1/ (k + rank + 1)
        docs[doc_id] = hit["_source"]

    sorted_ids= sorted(scores.keys(), key=lambda x: scores[x], reverse = True )

    return [
        {**docs[doc_id], "rrf_score": scores[doc_id]}
        for doc_id in sorted_ids[: top_k]
    ]