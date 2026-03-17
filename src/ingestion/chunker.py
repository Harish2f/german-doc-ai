from dataclasses import dataclass
from src.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE=500 # words per chunk
CHUNK_OVERLAP=50 # words of overlap between chunks

@dataclass
class Chunk:
    """A text chunk from a document ready for embedding and indexing.
    
    Args:
        text: The chunk content.
        doc_id: ID of the parent document.
        chunk_index: Position of this chunk in the document.
        doc_type: Document type inherited from parent.
        source_url=Source URL inherited from Parent.
    """
    text: str
    doc_id: str
    chunk_index: int
    doc_type: str
    source_url : str


def chunk_text(
        text:str,
        doc_id: str,
        doc_type: str,
        source_url: str,
        chunk_size: int=CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
)->list[Chunk]:
    """Spli Document text into overlapping chunks.
    
    Uses fixed size word based chunking with overlap to preserve context at chunk boundaries.
    Each chunk inherits metadata from the parent document.

    Args:
        text: Full document text to chunk.
        doc_id: Parent Document ID.
        doc_type: Parent Document Type.
        source_url: Parent Document source URL.
        chunk_size: Number of words per chunk.
        overlap: Number of words to repeat from previous chunk.

    Returns:
        List of Chunk objects ready for embedding. 
    """
    words = text.split()
    chunks=[]

    if not words:
        logger.warning("empty_document", doc_id=doc_id)
        return chunks
    
    start = 0
    chunk_index=0

    while start<len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_content = " ".join(chunk_words)

        chunks.append(Chunk(
            text=chunk_text_content,
            doc_id=doc_id,
            chunk_index=chunk_index,
            doc_type=doc_type,
            source_url=source_url,
        ))

        logger.debug(
            "chunk_created",
            doc_id=doc_id,
            chunk_index=chunk_index,
            word_count=len(chunk_words),
        )

        chunk_index += 1
        start = end - overlap
    
    logger.info(
        "document_created",
        doc_id=doc_id,
        total_chunks=len(chunks),
        total_words=len(words),
    )
    return chunks