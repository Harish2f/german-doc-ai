import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.logger import setup_logging, get_logger
from src.routers import health, documents, ingest
from src.dependencies import get_request_id
from src.db.postgres import init_db
from src.db.opensearch import init_opensearch
from src.routers import ask

setup_logging()
logger = get_logger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Application Startup and shutdown.
    
    Lifespan replaces the depricated @app.on_event handlers.
    Code before yield runs on startup and code after yield runs on shutdown.
    """
    logger.info(
        "germandocai_starting",
        environment= settings.environment,
        version=settings.app_version,
    )
    await init_db()
    await init_opensearch()
    yield
    logger.info("germandocai_stopping")


app = FastAPI(
    title = "GermanDocAI",
    description="Production RAG system for German Regulatory Documents Intelligence",
    version= settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with a unique request ID.

    Bind request_id to structlog context so every log line
    produced during this request includes the request ID.
    """
    request_id = get_request_id()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    logger.info(
        "request_started",
        method = request.method,
        path=request.url.path,
    )

    response = await call_next(request)

    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response

app.include_router(health.router, tags=["health"])
app.include_router(documents.router)
app.include_router(ingest.router)
app.include_router(ask.router)