import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from src.db.opensearch import get_opensearch
from src.search.retriever import hybrid_search
from src.models.document import DocumentType
from src.dependencies import get_request_id, verify_api_key
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ask", tags=["search"])

class AskRequest(BaseModel):
    """Request body for the Ask Endpoint."""
    query:str = Field(description="Query from the user in German or English")
    doc_types: list[DocumentType] = Field(default_factory=list,
                                          description="Optional Filter by Document Type.")
    top_K: int = Field(default = 5, description="Number of chunks to retrieve.")


class ChunkResult(BaseModel):
    """A single retrieved chunk from with metadata."""
    text: str
    doc_id: str
    doc_type: str
    source_url: str
    chunk_index: int
    rrf_score: float


class AskResponse(BaseModel):
    """Response from the Ask Endpoint."""
    query:str
    chunks: list[ChunkResult]
    total_chunks: int


@router.post("/", response_model=AskResponse)
async def ask(
    request: AskRequest,
    api_key: str = Depends(verify_api_key),
    opensearch=Depends(get_opensearch),
)-> AskResponse:
    """Retrieve relevant document chunks for a query.
    
    Performs Hybrid BM25 search + semantic search and returns
    the top-K most relevant chunks. These chunks will be passed to the Azure OpenAi to generate final Answer.

    Requires x_api_key Header. 
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("ask_request_received", query=request.query)

    doc_type_values = [dt.value for dt in request.doc_types] if request.doc_types is False else None

    try:
        results = await hybrid_search(
            query=request.query,
            client=opensearch,
            doc_types=doc_type_values,
            top_k=request.top_K,
        ) 
    except Exception as e:
        logger.error("search_failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    chunks = [
        ChunkResult(
            text=r["text"],
            doc_id=r["doc_id"],
            doc_type=r["doc_type"],
            source_url = r["source_url"],
            chunk_index = r["chunk_index"],
            rrf_score = r["rrf_score"],
        )
        for r in results
    ]

    logger.info(
        "ask_request_completed",
        query=request.query,
        chunks_returned=len(chunks),
    )
    return AskResponse(
        query=request.query,
        chunks= chunks,
        total_chunks=len(chunks),
    )