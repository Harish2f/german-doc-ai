import structlog
from src.logger import setup_logging, get_logger

def test_setup_logging_runs_without_error():
    """Verify logging setup does not raise any exceptions."""
    setup_logging()


def test_get_logger_returns_bound_logger():
    """Verify get_logger returns a structlog BoundLogger instance."""
    setup_logging()
    logger = get_logger(__name__)
    assert logger is not None


def test_logger_has_correct_methods():
    """Verify logger exposes standard log level methods."""
    setup_logging()
    logger = get_logger("test_component")
    assert hasattr(logger,'info')
    assert hasattr(logger,'error')
    assert hasattr(logger,'debug')
    assert hasattr(logger,'warning')


def test_get_logger_with_module_name():
    """Verify logger works with __name__ pattern used throughout the project."""
    setup_logging()
    logger = get_logger(__name__)
    assert logger is not None
