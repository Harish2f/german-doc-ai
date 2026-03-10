import pytest
from fastapi.testclient import TestClient
from src.main import app

VALID_API_KEY= "dev-secret-key"
HEADERS = {"x-api-key":VALID_API_KEY}

@pytest.fixture
def client():
    """FastAPI Test client availabl to all tests."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid API key Headers available to all tests"""
    return HEADERS