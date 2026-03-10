from fastapi import APIRouter, Depends, HTTPException
from src.models.document import Document, DocumentType
from src.logger import get_logger
from src.dependencies import verify_api_key, get_request_id
import structlog

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# In-memory store for now — replaced with OpenSearch
_documents: dict[str, Document] = {}

@router.post("/",status_code=201)
async def create_document(document: Document, 
                          api_key: str = Depends(verify_api_key),)-> Document:
    """Store a new document.
    
    Requires x_api_key header. Returns 409 if document ID already exists.
    This will persist to OpenSearch instead of memory.
    
    Args:
        document: Document to store, validated by Pydantic.
        api_key: Injected by verify_api_key dependency.
        
    Returns:
        The stored document.
    """
    request_id = get_request_id()
    structlog.contextvars.bind_contextvars(request_id = request_id)

    logger.info("create_document_called", doc_id=document.id)

    if document.id in _documents:
        logger.warning("document_already_exists", doc_id=document.id)
        raise HTTPException(
            status_code = 409,
            detail = f"Document with id '{document.id}' already exists"
        )
    
    _documents[document.id]= document
    logger.info("document_stored", doc_id=document.id, doc_type = document.doc_type)
    return document


@router.get("/{doc_id}")
async def get_document(doc_id: str, 
                       api_key = Depends(verify_api_key),)-> Document:
    """Retrieve a document by ID.
    
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

    if doc_id not in _documents:
        logger.warning("document_not_found", doc_id=doc_id)
        raise HTTPException(
            status_code = 404,
            detail = f"Document with id '{doc_id}' not found"
        )
    
    document = _documents[doc_id]
    logger.info("document_retrieved", doc_id=doc_id)
    return document