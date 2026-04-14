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

    # Mock the Azure client used inside grade_documents
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"relevant": true}'))],
        usage=MagicMock(prompt_tokens=50, completion_tokens=5),
    )
    mocker.patch(
        "src.agent.nodes.get_azure_openai_client",
        return_value=mock_client,
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