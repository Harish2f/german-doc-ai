import logging
import sys
import structlog
from src.config import get_settings

def setup_logging() -> None:
    """Configure Structlog for the application.
    
    In development: human readable coloured output in the terminal.
    In Production: JSON output for Azure Monitor ingestion.
    
    Call this once at application startup before any logging occurs. 
    """

    settings = get_settings()
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # configure standard library logging first
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level
    )

    # choose renderer based on environment
    if settings.environment.lower() == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class= dict,
        logger_factory= structlog.PrintLoggerFactory(),
    )


def get_logger(name: str) -> structlog.BoundLogger :
    """Get a logger instance bound to a specific component name.
    Args:
        name: Component name that appears in every log line.
               Use the module name for consistency: get_logger(__name__)
               
    Returns:
        A structlog BoundLogger with the component name pre-bound.
        
    Example:
        logger = get_logger(__name__)
        logger.info("document_processed", doc_id="bafin_001", duration_ms=234)
    """
    return structlog.get_logger(name)