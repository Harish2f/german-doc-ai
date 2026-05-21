import pytest
import os
from unittest.mock import AsyncMock, patch

from src.ingestion.docling_parser import ParsedDocument, parse_document_from_url


@pytest.mark.asyncio
async def test_parse_document_falls_back_to_pypdf(mocker):
    """Test that pypdf fallback is used when Docling fails."""
    fallback_doc = ParsedDocument(
        content="Fallback PDF text",
        page_count=1,
        source_url="https://example.com/test.pdf",
    )

    fallback_mock = mocker.patch(
        "src.ingestion.docling_parser.parse_pdf_with_pypdf",
        new_callable=AsyncMock,
        return_value=fallback_doc,
    )

    # Make docling import fail inside the function
    with patch.dict("sys.modules", {"docling.document_converter": None}):
        parsed = await parse_document_from_url("https://example.com/test.pdf")

    assert parsed == fallback_doc
    fallback_mock.assert_called_once_with("https://example.com/test.pdf")


@pytest.mark.asyncio
async def test_parse_document_uses_pypdf_in_production(mocker):
    """Test that production environment uses pypdf directly."""
    fallback_doc = ParsedDocument(
        content="Production PDF text",
        page_count=3,
        source_url="https://example.com/test.pdf",
    )

    fallback_mock = mocker.patch(
        "src.ingestion.docling_parser.parse_pdf_with_pypdf",
        new_callable=AsyncMock,
        return_value=fallback_doc,
    )

    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        parsed = await parse_document_from_url("https://example.com/test.pdf")

    assert parsed == fallback_doc
    fallback_mock.assert_called_once_with("https://example.com/test.pdf")