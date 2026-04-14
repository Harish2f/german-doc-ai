import json
from src.agent.state import AgentState
from src.rag.generator import get_azure_openai_client
from src.search.retriever import hybrid_search
from src.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)


async def retrieve(state: AgentState, opensearch_client) -> dict:
    """Retrieve relevant chunks from OpenSearch.
    
    Uses hybrid BM25 + semantic search with the current query
    (original or rewritten).
    
    Args:
        state: Current agent state.
        opensearch_client: Async OpenSearch client.
        
    Returns:
        Updated state with retrieved chunks.
    """
    query = state.get("rewritten_query") or state["query"]
    doc_types = state.get("doc_types", [])

    logger.info("agent_retrieving", query=query)

    chunks = await hybrid_search(
        query=query,
        client=opensearch_client,
        doc_types=doc_types if doc_types else None,
        top_k=5,
    )

    logger.info("agent_retrieved", chunk_count=len(chunks))
    return {"chunks": chunks}


async def grade_documents(state: AgentState) -> dict:
    """Grade retrieved chunks for relevance to the query.
    
    Uses GPT-4o to evaluate whether each chunk contains
    information relevant to answering the query.
    
    Returns:
        Updated state with documents_relevant flag.
    """
    query = state["query"]
    chunks = state["chunks"]

    if not chunks:
        logger.warning("agent_no_chunks_to_grade")
        return {"documents_relevant": False}

    client = get_azure_openai_client()
    settings = get_settings()

    grading_prompt = f"""You are grading whether retrieved documents are relevant to a question.

Question: {query}

Retrieved chunks:
{chr(10).join([f"Chunk {i+1}: {chunk['text'][:300]}" for i, chunk in enumerate(chunks)])}

Are these chunks relevant to answering the question?
Respond with JSON only: {{"relevant": true}} or {{"relevant": false}}"""

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[{"role": "user", "content": grading_prompt}],
        temperature=0.0,
        max_tokens=50,
    )

    result = response.choices[0].message.content.strip()
    
    try:
        parsed = json.loads(result)
        relevant = parsed.get("relevant", False)
    except json.JSONDecodeError:
        relevant = "true" in result.lower()

    logger.info("agent_graded_documents", relevant=relevant)
    return {"documents_relevant": relevant}


async def rewrite_query(state: AgentState) -> dict:
    """Rewrite the query for better retrieval.
    
    Uses GPT-4o to reformulate the query using domain-specific
    regulatory terminology that better matches document content.
    
    Returns:
        Updated state with rewritten_query and incremented rewrite_count.
    """
    query = state["query"]
    rewrite_count = state.get("rewrite_count", 0)

    client = get_azure_openai_client()
    settings = get_settings()

    rewrite_prompt = f"""You are improving a search query for a German regulatory document database.

    Original query: {query}

    Rewrite this query to use precise regulatory and legal terminology 
    that would appear in BaFin, EU AI Act, or DSGVO documents.
    Respond with only the rewritten query, nothing else."""

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[{"role": "user", "content": rewrite_prompt}],
        temperature=0.0,
        max_tokens=100,
    )

    rewritten = response.choices[0].message.content.strip()
    logger.info("agent_rewrote_query", original=query, rewritten=rewritten)

    return {
        "rewritten_query": rewritten,
        "rewrite_count": rewrite_count + 1,
    }


async def generate(state: AgentState) -> dict:
    """Generate final answer from retrieved chunks.
    
    Passes the query and relevant chunks to Azure OpenAI
    to synthesize a cited answer.
    
    Returns:
        Updated state with generation.
    """
    from src.rag.generator import generate_answer

    query = state.get("rewritten_query") or state["query"]
    chunks = state["chunks"]

    logger.info("agent_generating", query=query, chunk_count=len(chunks))

    result = await generate_answer(query=query, chunks=chunks)

    logger.info("agent_generated", prompt_tokens=result["prompt_tokens"])
    return {"generation": result["answer"]}


def grade_query(state: AgentState) -> str:
    """Decide if the query is answerable with our document corpus.
    
    This is a conditional edge function — returns a string
    that LangGraph uses to route to the next node.
    
    Returns:
        'retrieve' if query is answerable, 'out_of_scope' otherwise.
    """
    query = state["query"].lower()

    regulatory_keywords = [
        "bafin", "regulation", "requirement", "compliance", "dsgvo", "gdpr",
        "eu ai act", "mifid", "dora", "mitar", "micar", "banking", "financial",
        "risk", "audit", "supervisory", "regulatory", "directive", "artikel",
        "verordnung", "gesetz", "vorschrift", "datenschutz",
    ]

    if any(keyword in query for keyword in regulatory_keywords):
        logger.info("agent_query_in_scope", query=query)
        return "retrieve"

    logger.warning("agent_query_out_of_scope", query=query)
    return "out_of_scope"


def should_rewrite(state: AgentState) -> str:
    """Decide whether to rewrite the query or generate an answer.
    
    Conditional edge after document grading.
    
    Returns:
        'generate' if documents are relevant.
        'rewrite' if documents are not relevant and rewrites remain.
        'generate' if max rewrites reached (fallback).
    """
    relevant = state.get("documents_relevant", False)
    rewrite_count = state.get("rewrite_count", 0)
    max_rewrites = 2

    if relevant:
        return "generate"

    if rewrite_count < max_rewrites:
        logger.info("agent_rewriting", rewrite_count=rewrite_count)
        return "rewrite"

    logger.warning("agent_max_rewrites_reached", rewrite_count=rewrite_count)
    return "generate"