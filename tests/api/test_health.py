import pytest
from src.routers.health import health_check

def test_health_check(client):
    response = client.get("/health")
    assert response.json()["status"]=="ok"
    assert response.json()["service"]=="GermanDocAI"


def test_health_no_auth_required(client):
    response = client.get("/health")
    assert response.status_code == 200


