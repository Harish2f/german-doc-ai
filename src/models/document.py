from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    BAFIN = "bafin"
    EU_AI_ACT = "eu_ai_act"
    DSGVO = "dsgvo"
    BUNDESBANK = "bundesbank"
    OTHER = "other"


class Document(BaseModel):
    id: str
    title:str
    content: str
    doc_type: DocumentType
    source_url: str = ""
    page_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def word_count(self) -> int:
        return len(self.content.split())
    
    def short_preview(self, chars: int = 200) -> str:
        if len(self.content) <= chars:
            return self.content
        return self.content[:chars] + "..."
    
    def is_regulatory(self) -> bool:
        return self.doc_type != DocumentType.OTHER
    
    def to_dict(self) -> dict:
        return self.model_dump()
        
    @classmethod
    def create_document_from_url(cls, url :str, title:str, doc_type :DocumentType) -> "Document":
        return cls(id = url, 
                   title = title,
                   content = "",
                doc_type = doc_type,
                source_url = url ,
                )