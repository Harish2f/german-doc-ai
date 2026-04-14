import pytest
from unittest.mock import AsyncMock, patch, MagicMock

SAMPLE_CHUNKS = [
    {
        "doc_id": "doc_test001",
        "text": "BaFin requires AI models to be explainable.",
        "chunk_index": 0,
        "doc_type": "bafin",
        "source_url": "https://bafin.de/test.pdf",
        "rrf_score": 0.031,
    }
]


@pytest.mark.asyncio
async def test_run_agent(mocker):
    mock_opensearch = AsyncMock()

    mocker.patch(
        "src.agent.nodes.hybrid_search",
        new_callable=AsyncMock,
        return_value=SAMPLE_CHUNKS,
    )

    mocker.patch(
        "src.agent.nodes.grade_documents",
        new_callable=AsyncMock,
        return_value={"documents_relevant": True},
    )

    mocker.patch(
    "src.rag.generator.generate_answer",
    new_callable=AsyncMock,
    return_value={
        "answer": "BaFin requires AI models to be explainable.",
        "sources": ["doc_test001"],
        "prompt_tokens": 100,
        "completion_tokens": 20,
        },
    )

    from src.agent.graph import run_agent
    result = await run_agent(
        query="What does BaFin require for AI?",
        opensearch_client=mock_opensearch,
    )

    assert "answer" in result
    assert result["answer"] != ""


def test_out_of_scope_response():
    from src.agent.graph import out_of_scope_response
    state = {"query": "What is the weather today?",
             "rewritten_query":"",
            "doc_types":[],
            "chunks":[],
            "generation":"",
            "rewrite_count":0,
            "documents_relevant":False
             }
    result = out_of_scope_response(state)
    assert "generation" in result
    assert len(result["generation"]) > 0