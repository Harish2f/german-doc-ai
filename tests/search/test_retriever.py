import pytest
from unittest.mock import AsyncMock, MagicMock, patch


SAMPLE_CHUNKS = [
    {
        "text": "BaFin monitors cyber risks in financial institutions.",
        "doc_id": "doc_1",
        "chunk_index": 0,
        "doc_type": "bafin",
        "source_url": "https://bafin.de/test.pdf",
        "page_number": 0,
        "section_reference": "",
        "rrf_score": 0.016,
    },
    {
        "text": "BaFin requires DORA compliance for digital resilience.",
        "doc_id": "doc_1",
        "chunk_index": 1,
        "doc_type": "bafin",
        "source_url": "https://bafin.de/test.pdf",
        "page_number": 0,
        "section_reference": "",
        "rrf_score": 0.015,
    },
]


@pytest.mark.asyncio
async def test_hybrid_search_returns_reranked_chunks(mocker):
    """Test hybrid search retrieves and reranks chunks."""
    mocker.patch(
        "src.search.retriever.generate_embeddings",
        new_callable=AsyncMock,
        return_value=[[0.1] * 768],
    )
    mocker.patch(
        "src.search.retriever.chunk_repository.hybrid_search",
        new_callable=AsyncMock,
        return_value=SAMPLE_CHUNKS,
    )
    reranked = [
        {**SAMPLE_CHUNKS[0], "rerank_score": 0.95},
        {**SAMPLE_CHUNKS[1], "rerank_score": 0.87},
    ]
    mocker.patch(
        "src.search.retriever.rerank_chunks",
        new_callable=AsyncMock,
        return_value=reranked,
    )

    mock_db = AsyncMock()

    from src.search.retriever import hybrid_search
    result = await hybrid_search(
        query="What are BaFin cyber risk requirements?",
        client=None,
        doc_types=["bafin"],
        top_k=2,
        db=mock_db,
    )

    assert len(result) == 2
    assert result[0]["rerank_score"] == 0.95


@pytest.mark.asyncio
async def test_hybrid_search_raises_without_db(mocker):
    """Test hybrid search raises ValueError when db is None."""
    from src.search.retriever import hybrid_search
    with pytest.raises(ValueError, match="db session is required"):
        await hybrid_search(
            query="test",
            client=None,
            db=None,
        )


@pytest.mark.asyncio
async def test_hybrid_search_returns_empty_when_no_candidates(mocker):
    """Test hybrid search returns empty list when no chunks found."""
    mocker.patch(
        "src.search.retriever.generate_embeddings",
        new_callable=AsyncMock,
        return_value=[[0.1] * 768],
    )
    mocker.patch(
        "src.search.retriever.chunk_repository.hybrid_search",
        new_callable=AsyncMock,
        return_value=[],
    )

    mock_db = AsyncMock()

    from src.search.retriever import hybrid_search
    result = await hybrid_search(
        query="test query",
        client=None,
        doc_types=["bafin"],
        top_k=5,
        db=mock_db,
    )

    assert result == []