from src.observability.langfuse_client import init_langfuse
init_langfuse()

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.logger import setup_logging, get_logger
from src.routers import health, documents, ingest, ask, compliance
from src.dependencies import get_request_id
from src.db.postgres import init_db
import gradio as gr
from src.ui import demo

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


# create Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("germandocai_starting", version=settings.app_version, environment=settings.environment)
    await init_db()
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False
        DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        logger.info("docling_models_warmed_up")
    except Exception as e:
        logger.warning("docling_warmup_failed", error=str(e))
    yield
    logger.info("germandocai_stopping")


# create app
app = FastAPI(
    title="GermanDocAI",
    description="RAG system for German regulatory documents",
    version=settings.app_version,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# Mount Gradio UI
app = gr.mount_gradio_app(app, demo, path="/ui")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = get_request_id()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("request_started", method=request.method, path=request.url.path)
    response = await call_next(request)
    logger.info("request_completed", method=request.method, path=request.url.path, status_code=response.status_code)
    return response

app.include_router(health.router, tags=["health"])
app.include_router(documents.router)
app.include_router(ingest.router)
app.include_router(ask.router)
app.include_router(compliance.router)