import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi import UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from src.db.chunks import chunk_repository
from src.ingestion.docling_parser import parse_document_from_url
from src.ingestion.chunker import chunk_text
from src.ingestion.embedder import generate_embeddings
from src.models.document import DocumentType
from src.db.postgres import get_db, get_session_factory
from src.db.models import DocumentRecord
from src.dependencies import verify_api_key, get_request_id
from src.logger import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/ingestion", tags=["ingestion"])

class IngestRequest(BaseModel):
    """Request body for document ingestion endpoint."""
    url: str = Field(description="Public URL of the PDF to ingest")
    title: str = Field(description="Human readable document title")
    doc_type: DocumentType = Field(description="Regulatory Document Type")


class IngestResponse(BaseModel):
    """Response after successful document ingestion."""
    doc_id: str
    title: str
    page_count: int
    chunk_count: int
    message: str



async def _run_ingestion(
    doc_id: str,
    request_url: str,
    request_title: str,
    doc_type_value: str,
):
    """Background task for document ingestion."""
    from src.db.postgres import get_engine
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    engine = get_engine()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        try:
            logger.info("background_ingestion_started", doc_id=doc_id, url=request_url)
            parsed = await parse_document_from_url(request_url)
            chunks = chunk_text(
                text=parsed.content,
                doc_id=doc_id,
                doc_type=doc_type_value,
                source_url=request_url,
            )
            chunk_texts_list = [chunk.text for chunk in chunks]
            embeddings = await generate_embeddings(chunk_texts_list)
            chunk_dicts = [
                {
                    "doc_id": chunk.doc_id,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "doc_type": chunk.doc_type,
                    "source_url": chunk.source_url,
                    "page_number": chunk.page_number,
                    "section_reference": chunk.section_reference,
                    "embedding": embeddings[i],
                }
                for i, chunk in enumerate(chunks)
            ]

            # INSERT DOCUMENT RECORD FIRST to satisfy FK constraint
            existing = await db.execute(
                select(DocumentRecord).where(DocumentRecord.id == doc_id)
            )
            if existing.scalar_one_or_none() is None:
                record = DocumentRecord(
                    id=doc_id,
                    title=request_title,
                    doc_type=doc_type_value,
                    source_url=request_url,
                    page_count=parsed.page_count,
                )
                db.add(record)
                await db.flush()  # write to DB before inserting chunks

            # THEN insert chunks
            await chunk_repository.insert_chunks(db, chunk_dicts)
            await db.commit()
            logger.info("background_ingestion_completed", doc_id=doc_id, chunk_count=len(chunks))
        except Exception as e:
            logger.error("background_ingestion_failed", doc_id=doc_id, error=str(e))


@router.post("/", status_code=202, response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    doc_id = f"doc_{uuid.uuid5(uuid.NAMESPACE_URL, request.url).hex[:12]}"
    logger.info("ingest_request_received", url=request.url, title=request.title, doc_id=doc_id)

    # Check for duplicate before queuing
    existing = await db.execute(
        select(DocumentRecord).where(DocumentRecord.id == doc_id)
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("document_already_exists", doc_id=doc_id)
        return IngestResponse(
            doc_id=doc_id,
            title=request.title,
            page_count=0,
            chunk_count=0,
            message="Document already exists — skipping ingestion.",
        )

    # Queue background ingestion
    background_tasks.add_task(
        _run_ingestion,
        doc_id=doc_id,
        request_url=request.url,
        request_title=request.title,
        doc_type_value=request.doc_type.value,
    )

    return IngestResponse(
        doc_id=doc_id,
        title=request.title,
        page_count=0,
        chunk_count=0,
        message=f"Ingestion started for '{request.title}'. Document will be available shortly.",
    )


async def _run_ingestion_from_bytes(
    doc_id: str,
    file_bytes: bytes,
    filename: str,
    request_title: str,
    doc_type_value: str,
):
    """Background task for file upload ingestion."""
    from src.db.postgres import get_engine
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from src.ingestion.docling_parser import parse_document_from_bytes

    engine = get_engine()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        try:
            logger.info("background_upload_started", doc_id=doc_id, filename=filename)
            parsed = await parse_document_from_bytes(
                file_bytes=file_bytes,
                filename=filename,
                source_url=filename,
            )
            chunks = chunk_text(
                text=parsed.content,
                doc_id=doc_id,
                doc_type=doc_type_value,
                source_url=filename,
            )
            chunk_texts_list = [chunk.text for chunk in chunks]
            embeddings = await generate_embeddings(chunk_texts_list)
            chunk_dicts = [
                {
                    "doc_id": chunk.doc_id,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "doc_type": chunk.doc_type,
                    "source_url": chunk.source_url,
                    "page_number": chunk.page_number,
                    "section_reference": chunk.section_reference,
                    "embedding": embeddings[i],
                }
                for i, chunk in enumerate(chunks)
            ]

            existing = await db.execute(
                select(DocumentRecord).where(DocumentRecord.id == doc_id)
            )
            if existing.scalar_one_or_none() is None:
                record = DocumentRecord(
                    id=doc_id,
                    title=request_title,
                    doc_type=doc_type_value,
                    source_url=filename,
                    page_count=parsed.page_count,
                )
                db.add(record)
                await db.flush()

            await chunk_repository.insert_chunks(db, chunk_dicts)
            await db.commit()
            logger.info("background_upload_completed", doc_id=doc_id, chunk_count=len(chunks))
        except Exception as e:
            logger.error("background_upload_failed", doc_id=doc_id, error=str(e))


@router.post("/upload", status_code=202, response_model=IngestResponse)
async def ingest_document_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: DocumentType = Form(...),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("ingest_upload_received", filename=file.filename, title=title)

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    doc_id = f"doc_{uuid.uuid5(uuid.NAMESPACE_URL, file.filename + title).hex[:12]}"

    existing = await db.execute(
        select(DocumentRecord).where(DocumentRecord.id == doc_id)
    )
    if existing.scalar_one_or_none() is not None:
        return IngestResponse(
            doc_id=doc_id,
            title=title,
            page_count=0,
            chunk_count=0,
            message="Document already exists — skipping ingestion.",
        )

    background_tasks.add_task(
        _run_ingestion_from_bytes,
        doc_id=doc_id,
        file_bytes=file_bytes,
        filename=file.filename,
        request_title=title,
        doc_type_value=doc_type.value,
    )

    return IngestResponse(
        doc_id=doc_id,
        title=title,
        page_count=0,
        chunk_count=0,
        message=f"Upload received for '{title}'. Document will be available shortly.",
    )


@router.get("/{doc_id}/status")
async def get_ingestion_status(
    doc_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a document has been fully ingested and is ready to query."""
    from sqlalchemy import text as sql_text

    existing = await db.execute(
        select(DocumentRecord).where(DocumentRecord.id == doc_id)
    )
    doc = existing.scalar_one_or_none()

    if doc is None:
        return {
            "doc_id": doc_id,
            "status": "processing",
            "message": "Document is being processed. Please wait.",
            "chunk_count": 0,
        }

    result = await db.execute(
        sql_text("SELECT COUNT(*) FROM document_chunks WHERE doc_id = :doc_id"),
        {"doc_id": doc_id}
    )
    chunk_count = result.scalar()

    if chunk_count == 0:
        return {
            "doc_id": doc_id,
            "status": "processing",
            "message": "Document record created. Chunks being indexed.",
            "chunk_count": 0,
        }

    return {
        "doc_id": doc_id,
        "status": "ready",
        "message": f"Document ready. {chunk_count} chunks indexed.",
        "chunk_count": chunk_count,
        "title": doc.title,
        "doc_type": doc.doc_type,
    }