import pytest
from unittest.mock import AsyncMock, patch
from src.ingestion.docling_parser import ParsedDocument

SAMPLE_PARSED_DOC = ParsedDocument(
    content="BaFin requires AI models to be explainable and auditable." * 100,
    page_count=10,
    source_url="https://bafin.de/test.pdf",
)

SAMPLE_EMBEDDING = [0.1] * 768

@pytest.fixture
def mock_docling(mocker):
    """Mock docling parser to avoid real PDF downloads."""
    return mocker.patch(
        "src.routers.ingest.parse_document_from_url",
        new_callable = AsyncMock,
        return_value = SAMPLE_PARSED_DOC,
    )

@pytest.fixture
def mock_embeddings(mocker):
    """Mock JINA embeddings to avoid real API calls."""
    return mocker.patch(
        "src.routers.ingest.generate_embeddings",
        new_callable=AsyncMock,
        return_value = [SAMPLE_EMBEDDING] * 50,
    )


@pytest.fixture
def mock_chunk_repository(mocker):
    """Mock chunk repository to avoid real database writes."""
    return mocker.patch(
        "src.routers.ingest.chunk_repository.insert_chunks",
        new_callable=AsyncMock,
        return_value=50,
    )


def test_ingest_document(client, auth_headers, mock_docling, mock_embeddings, mock_chunk_repository):
    response = client.post(
        "/ingestion/",
        json={
            "url": "https://bafin.de/test.pdf",
            "title":"BaFin Test Document",
            "doc_type":"bafin",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "BaFin Test Document"
    assert response.json()["page_count"] == 10
    assert response.json()["chunk_count"] > 0


def test_ingest_duplicate_document(client, auth_headers,mock_docling, mock_embeddings, mock_chunk_repository):
    """Test that ingesting the same URL twice returns 201 both times without error."""

    payload = {
        "url": "https://bafin.de/test.pdf",
        "title": "BaFin Test Document",
        "doc_type": "bafin",
    }

    # First ingestion
    response1 = client.post("/ingestion/", headers=auth_headers, json=payload)
    assert response1.status_code == 201
    assert response1.json()["title"] == "BaFin Test Document"
    assert response1.json()["page_count"] == 10
    assert response1.json()["chunk_count"] > 0

    # Second ingestion — same URL should not crash
    response2 = client.post("/ingestion/", headers=auth_headers, json=payload)
    assert response2.status_code == 201
    assert response2.json()["title"] == "BaFin Test Document"
    assert response2.json()["page_count"] == 10
    assert response2.json()["chunk_count"] > 0


def test_ingest_requires_auth(client, mock_docling, mock_embeddings, mock_chunk_repository):
    response = client.post(
        "/ingestion/",
        json={
            "url":"https://bafin.de/test.pdf",
            "title":"Test",
            "doc_type":"bafin",
        },
    )
    assert response.status_code == 401


def test_ingest_invalid_doc_type(client, auth_headers, mock_docling, mock_embeddings,mock_chunk_repository):
    response = client.post(
        "/ingestion/",
        json={
            "url":"https://bafin.de/test.pdf",
            "title":"Test",
            "doc_type":"invalid_type",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422