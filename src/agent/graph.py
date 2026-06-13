from functools import partial
from langgraph.graph import StateGraph, START, END
from src.agent.state import AgentState
from src.agent.nodes import (
    retrieve,
    grade_documents,
    rewrite_query,
    generate,
    grade_query,
    should_rewrite,
)
from src.logger import get_logger

logger = get_logger(__name__)

def out_of_scope_response(state: AgentState) -> dict:
    """Return a polite out-of-scope message.
    
    Called when grade_query determines the question is not
    related to German regulatory documents.
    """
    logger.warning("agent_out_of_scope", query=state["query"])
    return {
        "generation": (
            "I can only answer questions about German regulatory documents "
            "such as BaFin publications, EU AI Act, and DSGVO. "
            "Please rephrase your question in that context."
        )
    }


def create_rag_agent(pgvector_client=None):
    """Create and compile the RAG agent graph.
    
    Builds a StateGraph with nodes for retrieval, grading,
    query rewriting, and answer generation. Conditional edges
    implement the agent's decision-making logic.
    
    Args:
        pgvector_client: Async pgvector session passed to retrieve node.
        
    Returns:
        Compiled LangGraph runnable.
    """
    workflow = StateGraph(AgentState)


    # Add nodes
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate", generate)
    workflow.add_node("out_of_scope", out_of_scope_response)

    # Entry point — conditional edge from START
    workflow.add_conditional_edges(
        START,
        grade_query,
        {
            "retrieve": "retrieve",
            "out_of_scope": "out_of_scope",
        }
    )

    # After retrieval — grade the documents
    workflow.add_edge("retrieve", "grade_documents")

    # After grading — decide to generate or rewrite
    workflow.add_conditional_edges(
        "grade_documents",
        should_rewrite,
        {
            "generate": "generate",
            "rewrite": "rewrite_query",
        }
    )

    # After rewriting — retrieve again
    workflow.add_edge("rewrite_query", "retrieve")

    # Terminal nodes
    workflow.add_edge("generate", END)
    workflow.add_edge("out_of_scope", END)

    return workflow.compile()


async def run_agent(
    query: str,
    doc_types: list[str] | None = None,
    user_id: str = "anonymous",
    session_id: str | None = None,
    db=None,
) -> dict:
    """Run the RAG agent for a given query.
    
    Initialises state, compiles the graph, and executes
    the agent until it reaches END.
    
    Args:
        query: User's question in German or English.
        doc_types: Optional document type filters.
        
    Returns:
        Dict with generation, chunks, and rewrite_count.
    """
    graph = create_rag_agent()

    initial_state: AgentState = {
        "query": query,
        "rewritten_query": "",
        "doc_types": doc_types or [],
        "chunks": [],
        "generation": "",
        "rewrite_count": 0,
        "documents_relevant": False,
        "user_id": user_id,
        "session_id": session_id,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "db": db,
        }

    logger.info("agent_started", query=query)

    result = await graph.ainvoke(initial_state)

    logger.info(
        "agent_completed",
        query=query,
        rewrite_count=result.get("rewrite_count", 0),
        chunks_used=len(result.get("chunks", [])),
    )

    return {
        "answer": result["generation"],
        "chunks": result.get("chunks", []),
        "rewrite_count": result.get("rewrite_count", 0),
        "rewritten_query": result.get("rewritten_query", ""),
        "prompt_tokens": result.get("prompt_tokens", 0),
        "completion_tokens": result.get("completion_tokens", 0),
    }