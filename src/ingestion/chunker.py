import nltk
from dataclasses import dataclass
from src.logger import get_logger

logger = get_logger(__name__)

# Download sentence tokenizer on first use
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=False)

CHUNK_SIZE = 300      # target words per chunk
CHUNK_OVERLAP = 2     # sentences of overlap between chunks


@dataclass
class Chunk:
    """A text chunk from a document ready for embedding and indexing."""
    text: str
    doc_id: str
    chunk_index: int
    doc_type: str
    source_url: str
    page_number: int = 0
    section_reference: str = ""


def chunk_text(
    text: str,
    doc_id: str,
    doc_type: str,
    source_url: str,
    page_number: int = 0,
    section_reference: str = "",
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split document text into sentence-aware chunks.
    
    Splits at sentence boundaries targeting chunk_size words per chunk.
    Uses sentence-level overlap to preserve context at boundaries.
    Better than word-based chunking for regulatory documents where
    sentences contain complete regulatory concepts.

    Args:
        text: Full document text to chunk.
        doc_id: Parent document ID.
        doc_type: Parent document type.
        source_url: Parent document source URL.
        chunk_size: Target number of words per chunk.
        overlap: Number of sentences to repeat from previous chunk.

    Returns:
        List of Chunk objects ready for embedding.
    """
    if not text or not text.strip():
        logger.warning("empty_document", doc_id=doc_id)
        return []

    # Split into sentences
    sentences = nltk.sent_tokenize(text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if not sentences:
        logger.warning("no_sentences_found", doc_id=doc_id)
        return []

    chunks = []
    chunk_index = 0
    i = 0

    while i < len(sentences):
        current_sentences = []
        current_words = 0

        # Add sentences until we reach chunk_size words
        j = i
        while j < len(sentences):
            sentence_words = len(sentences[j].split())
            if current_words + sentence_words > chunk_size and current_sentences:
                break
            current_sentences.append(sentences[j])
            current_words += sentence_words
            j += 1

        if not current_sentences:
            # Single sentence exceeds chunk_size — include it anyway
            current_sentences = [sentences[i]]
            j = i + 1

        chunk_text_content = " ".join(current_sentences)

        chunks.append(Chunk(
            text=chunk_text_content,
            doc_id=doc_id,
            chunk_index=chunk_index,
            doc_type=doc_type,
            source_url=source_url,
            page_number=page_number,
            section_reference=section_reference,
        ))

        logger.debug(
            "chunk_created",
            doc_id=doc_id,
            chunk_index=chunk_index,
            word_count=current_words,
            sentence_count=len(current_sentences),
        )

        chunk_index += 1
        # Move back by overlap sentences for context continuity
        i = j - overlap if j - overlap > i else j

    logger.info(
        "document_chunked",
        doc_id=doc_id,
        total_chunks=len(chunks),
        total_sentences=len(sentences),
    )
    return chunks