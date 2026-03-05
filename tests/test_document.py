import pytest
from src.models.document import Document, DocumentType

def test_document_creation():
    doc = Document(
        id= 'doc_001',
        title="BaFin Annual Report 2023",
        content="This is the content of the BaFin annual report.",
        doc_type=DocumentType.BAFIN,
    )
    assert doc.id == 'doc_001'
    assert doc.title == 'BaFin Annual Report 2023'
    assert doc.doc_type == DocumentType.BAFIN
    assert doc.page_count == 0


def test_word_count():
    doc = Document(
        id = "doc_002",
        title = "Test Document",
        content = "one two threee four five",
        doc_type = DocumentType.DSVGO, 
    )
    assert doc.word_count() == 5

    
def test_short_preview_truncates():
    doc = Document(
        id = "doc_003",
        title = "Test",
        content = "A" * 500,
        doc_type = DocumentType.EU_AI_ACT,
    )
    preview = doc.short_preview()
    assert len(preview) == 203
    assert preview.endswith("...")


def test_short_preview_no_truncation():
    doc = Document(
        id = "doc_004",
        title = "Test",
        content = "Short form content",
        doc_type = DocumentType.DSVGO,
    )
    assert doc.short_preview() == "Short form content"


def test_is_regulatory_true():
    doc = Document(
        id = "doc_005",
        title = "Test",
        content = "Some regulatory content",
        doc_type = DocumentType.BAFIN,
    )
    assert doc.is_regulatory() is True


def test_is_regulatory_false():
    doc = Document(
        id = "doc_006",
        title = "Test",
        content = "Some non-regulatory content",
        doc_type = DocumentType.OTHER,
    )
    assert doc.is_regulatory() is False


def test_invalid_document_type():
    with pytest.raises(Exception):
        Document(
            id = "doc_007",
            title = "Test",
            content = "Content with invalid doc type",
            doc_type = "invalid_type",  
        )
