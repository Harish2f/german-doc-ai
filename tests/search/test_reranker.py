import pytest
from unittest.mock import MagicMock, patch


SAMPLE_CHUNKS = [
    {"text": "BaFin monitors cyber risks in financial institutions.", "doc_id": "doc_1", "chunk_index": 0, "rrf_score": 0.016},
    {"text": "The weather in Berlin is cold in winter.", "doc_id": "doc_2", "chunk_index": 0, "rrf_score": 0.015},
    {"text": "BaFin requires DORA compliance for digital resilience.", "doc_id": "doc_3", "chunk_index": 0, "rrf_score": 0.014},
]


@pytest.mark.asyncio
async def test_rerank_chunks_returns_top_k(mocker):
    """Test reranker returns correct number of chunks."""
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(index=0, relevance_score=0.95),
        MagicMock(index=2, relevance_score=0.87),
    ]

    mock_client = MagicMock()
    mock_client.rerank.return_value = mock_result

    mocker.patch("src.search.reranker.get_cohere_client", return_value=mock_client)

    from src.search.reranker import rerank_chunks
    result = await rerank_chunks(
        query="What are BaFin cyber risk requirements?",
        chunks=SAMPLE_CHUNKS,
        top_k=2,
    )

    assert len(result) == 2
    assert result[0]["rerank_score"] == 0.95
    assert result[1]["rerank_score"] == 0.87


@pytest.mark.asyncio
async def test_rerank_chunks_empty_input():
    """Test reranker handles empty chunk list."""
    from src.search.reranker import rerank_chunks
    result = await rerank_chunks(query="test", chunks=[], top_k=5)
    assert result == []


@pytest.mark.asyncio
async def test_rerank_chunks_falls_back_on_error(mocker):
    """Test reranker returns original chunks if Cohere fails."""
    mocker.patch(
        "src.search.reranker.get_cohere_client",
        side_effect=Exception("API error"),
    )

    from src.search.reranker import rerank_chunks
    result = await rerank_chunks(
        query="test query",
        chunks=SAMPLE_CHUNKS,
        top_k=2,
    )

    assert len(result) == 2
    assert result == SAMPLE_CHUNKS[:2]