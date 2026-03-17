import pytest
from unittest.mock import AsyncMock, patch

SAMPLE_SEARCH_RESULTS = [
    {
        "doc_id": "doc_test001",
        "text": "BaFin requires AI models to be explainable.",
        "chunk_index": 0,
        "doc_type": "bafin",
        "source_url": "https://bafin.de/test.pdf",
        "rrf_score": 0.031,
    }
]


@pytest.fixture
def mock_hybrid_search(mocker):
    """Mock hybrid search to avoid real API calls on Opensearch."""
    return mocker.patch(
        "src.routers.ask.hybrid_search",
        new_callable = AsyncMock,
        return_value = SAMPLE_SEARCH_RESULTS,
        )


def test_ask(client,auth_headers,mock_hybrid_search):
    response = client.post(
        "/ask/",
        json={
            "query":"What are the BaFin requirements for AI models to be explainable?",
            "doc_types":["bafin"],
            "top_k": 5
        },
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_ask_no_auth(client,mock_hybrid_search):
    response = client.post(
        "/ask/",
        json= {
            "query":"What are the BaFin requirements for AI models to be explainable?",
            "doc_types":["bafin"],
            "top_k": 5
        },
    )
    assert response.status_code == 401


def test_ask_returns_correct_fields(client,auth_headers,mock_hybrid_search):
    response = client.post(
        "/ask/",
        json = {
            "query":"What are the BaFin requirements for AI models to be explainable?",
            "doc_types":["bafin"],
            "top_k": 5
        },
        headers = auth_headers,
    )
    assert response.json()['query'] == "What are the BaFin requirements for AI models to be explainable?"
    assert isinstance(response.json()['chunks'] ,list)