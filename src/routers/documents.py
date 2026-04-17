from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.document import Document, DocumentType
from src.db.postgres import get_db, DocumentRecord
from src.logger import get_logger
from src.dependencies import verify_api_key, get_request_id
import structlog

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# In-memory store for now — replaced with OpenSearch
_documents: dict[str, Document] = {}

@router.post("/",status_code=201)
async def create_document(document: Document, 
                          api_key: str = Depends(verify_api_key),
                          db: AsyncSession= Depends(get_db))-> Document:
    """Store a new document.
    
    Requires x_api_key header. Returns 409 if document ID already exists.
    
    Args:
        document: Document to store, validated by Pydantic.
        api_key: Injected by verify_api_key dependency.
        db: db session for the request
        
    Returns:
        The stored document.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id = request_id)

    logger.info("create_document_called", doc_id=document.id)

    result= await db.execute(
        select(DocumentRecord).where(DocumentRecord.id==document.id)
    )
    existing= result.scalar_one_or_none()

    if existing:
        logger.warning("document_already_exists", doc_id=document.id)
        raise HTTPException(
            status_code = 409,
            detail = f"Document with id '{document.id}' already exists"
        )
    
    #store in postgreSQL
    record = DocumentRecord(
        id=document.id,
        title=document.title,
        doc_type=document.doc_type.value,
        source_url=document.source_url,
        page_count=document.page_count,
    )
    db.add(record)
    logger.info("document_stored", doc_id=document.id, doc_type = document.doc_type)
    return document


@router.get("/{doc_id}")
async def get_document(doc_id: str, 
                       api_key = Depends(verify_api_key),
                       db: AsyncSession = Depends(get_db),)-> Document:
    """Retrieve a document by ID from PostgreSQL.
    
    Requires x_api_key header. Returns 404 if document not found.
    
    Args:
        doc_id: Document ID from the URL path.
        api_key: Injected by verify_api_key dependency.
        
    Returns:
        The requested document.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    logger.info("get_document_called", doc_id=doc_id)

    result = await db.execute(
        select(DocumentRecord).where(DocumentRecord.id==doc_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        logger.warning("document_not_found", doc_id=doc_id)
        raise HTTPException(
            status_code = 404,
            detail = f"Document with id '{doc_id}' not found"
        )
    
    logger.info("document_retrieved", doc_id=doc_id)
    return Document(
        id=record.id,
        title=record.title,
        doc_type=DocumentType(record.doc_type),
        source_url=record.source_url or "",
        page_count=record.page_count or 0,
        created_at=record.created_at,
    )