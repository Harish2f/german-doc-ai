from unittest.mock import patch, MagicMock
import pytest

from src.observability.langfuse_client import init_langfuse, get_trace


@patch("src.observability.langfuse_client.get_settings")
@patch("src.observability.langfuse_client.logger")
def test_init_langfuse_missing_keys(mock_logger, mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.langfuse_public_key = None
    mock_settings.langfuse_secret_key = None
    mock_get_settings.return_value = mock_settings

    result = init_langfuse()

    assert result is False
    mock_logger.warning.assert_called_once_with("langfuse_not_configured")


@patch("src.observability.langfuse_client.get_settings")
@patch("src.observability.langfuse_client.logger")
def test_init_langfuse_success(mock_logger, mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.langfuse_public_key = "public-key"
    mock_settings.langfuse_secret_key = "secret-key"
    mock_settings.langfuse_host = "http://localhost:3000"

    mock_get_settings.return_value = mock_settings

    with patch.dict("os.environ", {}, clear=True):
        result = init_langfuse()

        assert result is True

        import os
        assert os.environ["LANGFUSE_PUBLIC_KEY"] == "public-key"
        assert os.environ["LANGFUSE_SECRET_KEY"] == "secret-key"
        assert os.environ["LANGFUSE_HOST"] == "http://localhost:3000"

    mock_logger.info.assert_called_once_with("langfuse_initialized")


@patch("src.observability.langfuse_client.get_client")
def test_get_trace_success(mock_get_client):
    mock_trace = MagicMock()

    mock_client = MagicMock()
    mock_client.trace.return_value = mock_trace

    mock_get_client.return_value = mock_client

    result = get_trace(
        name="test-trace",
        user_id="user-123",
        session_id="session-123",
        metadata={"env": "test"},
        tags=["rag", "evaluation"],
    )

    assert result == mock_trace

    mock_client.trace.assert_called_once_with(
        name="test-trace",
        user_id="user-123",
        session_id="session-123",
        metadata={"env": "test"},
        tags=["rag", "evaluation"],
    )


@patch("src.observability.langfuse_client.get_client")
def test_get_trace_defaults(mock_get_client):
    mock_trace = MagicMock()

    mock_client = MagicMock()
    mock_client.trace.return_value = mock_trace

    mock_get_client.return_value = mock_client

    result = get_trace(name="default-trace")

    assert result == mock_trace

    mock_client.trace.assert_called_once_with(
        name="default-trace",
        user_id="anonymous",
        session_id=None,
        metadata={},
        tags=[],
    )


@patch("src.observability.langfuse_client.get_client")
def test_get_trace_exception_returns_none(mock_get_client):
    mock_get_client.side_effect = Exception("Langfuse unavailable")

    result = get_trace(name="error-trace")

    assert result is None