from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    """Supported German regulatory document types.
    
    Using str mixin allows direct string comparison and JSON serialisation
    without calling .value explicitly.
    """
    BAFIN = "bafin"
    EU_AI_ACT = "eu_ai_act"
    DSGVO = "dsgvo"
    BUNDESBANK = "bundesbank"
    OTHER = "other"


class Document(BaseModel):
    """Represents a German regulatory document in the system.
    
    This is the core data model passed between all components —
    ingestion pipeline, search index, RAG pipeline, and API layer.
    
    Attributes:
        id: Unique identifier, typically the source URL or a generated UUID.
        title: Human-readable document title.
        content: Full extracted text content of the document.
        doc_type: Classification of the regulatory document type.
        source_url: Original URL where the document was retrieved from.
        page_count: Number of pages in the source PDF.
        created_at: Timestamp when this document was ingested.
    """
    id: str
    title:str
    content: str
    doc_type: DocumentType
    source_url: str = ""
    page_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def word_count(self) -> int:
        """Return the number of words in the document content."""
        return len(self.content.split())
    
    def short_preview(self, chars: int = 200) -> str:
        """Return a truncated preview of the document content.
        
        Args:
            chars: Maximum number of characters to return. Defaults to 200.
            
        Returns:
            Full content if shorter than chars, otherwise truncated with ellipsis.
        """
        if len(self.content) <= chars:
            return self.content
        return self.content[:chars] + "..."
    
    def is_regulatory(self) -> bool:
        """Return True if this is a regulatory document (not OTHER type)."""
        return self.doc_type != DocumentType.OTHER
    
    def to_dict(self) -> dict:
        """Return document as a plain Python dictionary.
        
        Uses Pydantic's model_dump() which handles datetime serialisation
        and enum value conversion automatically.
        """
        return self.model_dump()
        
    @classmethod
    def create_document_from_url(cls, url :str, title:str, doc_type :DocumentType) -> "Document":
        """Create a Document with empty content from a URL.
        
        Used during the ingestion pipeline when we have document metadata
        but have not yet fetched and parsed the content.
        
        Args:
            url: Source URL of the document, also used as the document ID.
            title: Human-readable title of the document.
            doc_type: Classification of the regulatory document type.
            
        Returns:
            A new Document instance with empty content field.
        """
        return cls(id = url, 
                   title = title,
                   content = "",
                doc_type = doc_type,
                source_url = url ,
                )