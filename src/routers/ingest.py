import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from src.db.postgres import get_db, DocumentRecord
from src.db.opensearch import get_opensearch
from src.ingestion.docling_parser import parse_document_from_url
from src.ingestion.chunker import chunk_text
from src.ingestion.embedder import generate_embeddings
from src.models.document import DocumentType
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


@router.post("/", status_code= 201, response_model = IngestResponse)
async def ingest_document(
    request: IngestRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
    opensearch=Depends(get_opensearch),
)-> IngestResponse:
    """Ingest a PDF document from the URL.
    
    Downloads and parses the PDF with docling, splits into chunks, 
    generates embeddings with JINA, store the chunks in Opensearch,
    and stores document metadata in PostgreSQL.

    Requires x_api_key header.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("ingest_request_received", url=request.url, title=request.title)

    # Generate Document ID from URL.
    doc_id = f"doc_{uuid.uuid5(uuid.NAMESPACE_URL, request.url).hex[:12]}"

    # step 1 - parse pdf with docling
    try:
        parsed = await parse_document_from_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code = 422,detail= str(e))
    
    # step 2 - Chunk the text
    chunks = chunk_text(
        text = parsed.content,
        doc_id = doc_id,
        doc_type = request.doc_type.value,
        source_url = request.url,
    )

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail = "Document produced no chunks - content may be empty."
        )
    
    # step 3 - Generate embeddings for all chunks in one batch
    chunk_texts = [chunk.text for chunk in chunks]
    embeddings = await generate_embeddings(chunk_texts)

    # step 4 - store chunks in OpenSearch
    for chunk, embedding in zip(chunks,embeddings):
        await opensearch.index(
            index="german-docs-chunks",
            body={
                "doc_id":chunk.doc_id,
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "doc_type": chunk.doc_type,
                "source_url":chunk.source_url,
                "embedding":embedding,
                "page_number":chunk.page_number,
                "section_reference":chunk.section_reference,
            }
        )

    # step 5 - store document metadata in PostgreSQL
    record = DocumentRecord(
        id=doc_id,
        title=request.title,
        doc_type=request.doc_type.value,
        source_url= request.url,
        page_count = parsed.page_count,
    )
    db.add(record)

    logger.info(
        "document_ingested",
        doc_id=doc_id,
        chunk_count = len(chunks),
        page_count = parsed.page_count,
    )

    return IngestResponse(
        doc_id = doc_id,
        title=request.title,
        page_count=parsed.page_count,
        chunk_count=len(chunks),
        message=f"Successfully ingested {len(chunks)} chunks from {parsed.page_count} pages",
    )

