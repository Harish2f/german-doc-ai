from typing import TypedDict, Annotated
from operator import add


class AgentState(TypedDict):
    """State passed between all nodes in the LangGraph agent.
    
    Every node receives the full state and returns a dict
    with only the fields it modified. LangGraph merges
    the updates back into the state automatically.
    
    Fields:
        query: Original user question.
        rewritten_query: Query after rewriting for better retrieval.
        doc_types: Optional document type filters.
        chunks: Retrieved document chunks from OpenSearch.
        generation: Final answer from Azure OpenAI.
        rewrite_count: Number of query rewrites attempted.
        documents_relevant: Whether retrieved chunks passed grading.
    """
    query: str
    rewritten_query: str
    doc_types: list[str]
    chunks: list[dict]
    generation: str
    rewrite_count: int
    documents_relevant: bool