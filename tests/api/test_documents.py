import pytest


def test_create_document(client,auth_headers):
    response = client.post(
        "/documents",
        json={
            'id':"test_001",
            "title":"Test Document",
            "content":"Test content for BaFin compliance",
            "doc_type":"bafin",
            "source_url":"https://bafin.de/test/pdf",
            "page_count":10,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["id"]=="test_001"
    assert response.json()['doc_type']=='bafin'


def test_create_document_no_auth(client):
    response = client.post(
         "/documents",
        json={
                "id":"test_002",
                "title":"test",
                "content":"Test content",
                "doc_type":"dsgvo",
            },
    )
    assert response.status_code==401


def test_create_document_invalid_auth(client):
    response = client.post(
            "/documents",
            json={
                "id":"test_003",
                "title":"Test",
                "content":"Content",
                "doc_type":"bafin",
            },
            headers = {'x-api-key':"wrong-key"},
    )
    assert response.status_code==401


def test_get_document(client,auth_headers):
    client.post(
             "/documents/",
        json={
            "id": "test_get_001",
            "title": "Get Test",
            "content": "Content for retrieval test.",
            "doc_type": "eu_ai_act",
            "source_url": "https://eu.europa.eu/test.pdf",
            "page_count": 5,
        },
        headers=auth_headers,
    )
    response = client.get("/documents/test_get_001", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Get Test"


def test_get_document_not_found(client,auth_headers):
    response = client.get("/documents/nonexistent_id", headers=auth_headers)
    assert response.status_code == 404


def test_get_document_no_auth(client):
    response = client.get("/documents/test_get_001")
    assert response.status_code == 401


def test_create_duplicate_document(client,auth_headers):
    client.post(
        "/documents/",
        json={
            "id": "duplicate_001",
            "title": "Original",
            "content": "Original content.",
            "doc_type": "dsgvo",
        },
        headers=auth_headers,
    )
    response = client.post(
        "/documents/",
        json={
            "id": "duplicate_001",
            "title": "Duplicate",
            "content": "Duplicate content.",
            "doc_type": "dsgvo",
        },
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_invalid_doc_type(client,auth_headers):
    response = client.post(
        "/documents/",
        json={
            "id": "invalid_001",
            "title": "Test",
            "content": "Content",
            "doc_type": "invalid_type",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422

