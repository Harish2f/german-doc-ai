import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from src.db.opensearch import get_opensearch
from src.search.retriever import hybrid_search
from src.models.document import DocumentType
from src.rag.generator import generate_answer
from src.rag.rate_limiter import llm_rate_limiter
from src.rag.circuit_breaker import llm_circuit_breaker, CircuitState
from src.dependencies import get_request_id, verify_api_key
from src.agent.graph import run_agent
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ask", tags=["search"])

class AskRequest(BaseModel):
    """Request body for the Ask Endpoint."""
    query:str = Field(description="Query from the user in German or English")
    doc_types: list[DocumentType] = Field(default_factory=list,
                                          description="Optional Filter by Document Type.")
    top_k: int = Field(default = 5, description="Number of chunks to retrieve.")


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
    answer:str
    sources: list[str]
    chunks: list[ChunkResult]
    total_chunks: int
    prompt_tokens: int
    completion_tokens: int


class AgentResponse(BaseModel):
    """Response from the agent endpoint."""
    query: str
    answer: str
    chunks: list[ChunkResult]
    rewrite_count: int
    rewritten_query: str



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

    doc_type_values = [dt.value for dt in request.doc_types] if request.doc_types else None

    try:
        results = await hybrid_search(
            query=request.query,
            client=opensearch,
            doc_types=doc_type_values,
            top_k=request.top_k,
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

    # check circuit breaker
    if not llm_circuit_breaker.can_attempt():
        raise HTTPException(
            status_code = 503,
            detail = "AI service temporarily unavailable. Please try again later."
        )
    # Apply rate limiting
    await llm_rate_limiter.acquire()

    # Generate answer with Azure OpenAI
    try:
        llm_response = await generate_answer(
            query=request.query,
            chunks=results,
        )
        llm_circuit_breaker.call_succeeded()
    except Exception as e:
        llm_circuit_breaker.call_failed()
        logger.error("llm_call_failed", query=request.query, error = str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to generate answer: {str(e)}"
        )

    logger.info(
        "ask_request_completed",
        query=request.query,
        chunks_returned=len(chunks),
        prompt_tokens=llm_response["prompt_tokens"],
        completion_tokens=llm_response["completion_tokens"],
    )

    return AskResponse(
        query=request.query,
        answer=llm_response["answer"],
        sources=llm_response["sources"],
        chunks= chunks,
        total_chunks=len(chunks),
        prompt_tokens = llm_response["prompt_tokens"],
        completion_tokens=llm_response["completion_tokens"],
    )

@router.post("/agent", response_model=AgentResponse)
async def ask_agent(
    request: AskRequest,
    api_key: str = Depends(verify_api_key),
    opensearch=Depends(get_opensearch),
) -> AgentResponse:
    """Answer a query using the LangGraph RAG agent.
    
    Unlike the basic ask endpoint, the agent can:
    - Detect out-of-scope queries
    - Grade retrieved documents for relevance
    - Rewrite queries for better retrieval
    - Run multiple retrieval rounds if needed
    
    Requires X-Api-Key header.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("agent_request_received", query=request.query)

    doc_type_values = [dt.value for dt in request.doc_types] if request.doc_types else None

    # Check circuit breaker
    if not llm_circuit_breaker.can_attempt():
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )

    # Apply rate limiting
    await llm_rate_limiter.acquire()

    try:
        result = await run_agent(
            query=request.query,
            opensearch_client=opensearch,
            doc_types=doc_type_values,
        )
        llm_circuit_breaker.call_succeeded()
    except Exception as e:
        llm_circuit_breaker.call_failed()
        logger.error("agent_failed", query=request.query, error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Agent failed: {str(e)}"
        )

    chunks = [
        ChunkResult(
            text=r["text"],
            doc_id=r["doc_id"],
            doc_type=r["doc_type"],
            source_url=r["source_url"],
            chunk_index=r["chunk_index"],
            rrf_score=r["rrf_score"],
        )
        for r in result["chunks"]
    ]

    return AgentResponse(
        query=request.query,
        answer=result["answer"],
        chunks=chunks,
        rewrite_count=result["rewrite_count"],
        rewritten_query=result["rewritten_query"],
    )