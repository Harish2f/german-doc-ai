import pytest
from unittest.mock import AsyncMock, patch, MagicMock

SAMPLE_CHUNKS = [
    {
        "doc_id":"doc_test001",
        "text":"BaFin requires AI models to be explainable.",
        "doc_type":"bafin",
        "source_url": "https://bafin.de/test.pdf",
        "chunk_index": 0,
    }
]

SAMPLE_LLM_RESPONSE = {
    "answer": "BaFin requires AI models to be explainable and auditable.",
    "sources":["doc_test001"],
    "prompt_tokens": 100,
    "completion_tokens":20,

}

@pytest.mark.asyncio
async def test_generate_answer():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
    choices = [MagicMock(message=MagicMock(content = "BaFin requires AI models to be explainable."))],
            usage = MagicMock(prompt_tokens=100, completion_tokens=20),
    )
    with patch("src.rag.generator.get_azure_openai_client", return_value=mock_client):
        from src.rag.generator import generate_answer
        result = await generate_answer(
            query = "What does BaFin require for AI?",
            chunks = SAMPLE_CHUNKS,
        )
    assert "answer" in result
    assert "sources" in result
    assert "prompt_tokens" in result
    assert "completion_tokens" in result
    assert result["sources"] == ["doc_test001"]


@pytest.mark.asyncio
async def test_generate_answer_returns_correct_structure():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices = [MagicMock(message=MagicMock(content="Test answer"))],
        usage = MagicMock(prompt_tokens = 50, completion_tokens=10),
    )
    with patch("src.rag.generator.get_azure_openai_client", return_value = mock_client):
        from src.rag.generator import generate_answer
        result = await generate_answer(
            query = "Test query",
            chunks = SAMPLE_CHUNKS,
        )
    assert isinstance(result["answer"], str)
    assert isinstance(result["sources"], list)
    assert isinstance(result["prompt_tokens"], int)
    assert isinstance(result["completion_tokens"], int)
