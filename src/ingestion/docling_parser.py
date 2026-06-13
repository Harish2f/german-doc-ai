import io
import os
import httpx
from dataclasses import dataclass
from pypdf import PdfReader
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedDocument:
    """Result of parsing a PDF document.
    
    Contains the extracted text content and metadata
    needed to create a Document and DocumentRecord.
    """
    content: str
    page_count: int
    source_url: str


async def parse_document_from_url(url: str) -> ParsedDocument:
    logger.info("parsing_document", url=url)

    # Try Docling first, fall back to pypdf
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False

        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )
        result = converter.convert(url)
        content = result.document.export_to_markdown()
        page_count = len(result.document.pages)

        logger.info(
            "document_parsed_docling",
            url=url,
            page_count=page_count,
            content_length=len(content),
        )
        return ParsedDocument(content=content, page_count=page_count, source_url=url)

    except Exception as e:
        logger.warning("docling_parser_failed", url=url, error=str(e))
        return await parse_pdf_with_pypdf(url)


async def parse_pdf_with_pypdf(url: str) -> ParsedDocument:
    """PDF text extraction using pypdf.
    
    Used in production and as fallback in development.
    Reliable for digital PDFs without system graphics library dependencies.
    Less accurate than Docling for complex layouts but works everywhere.

    Args:
        url: Public URL of the PDF to parse.

    Returns:
        ParsedDocument with extracted text and metadata.

    Raises:
        ValueError: If the PDF cannot be fetched or has no extractable text.
    """
    logger.info("parsing_document_pypdf", url=url)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_bytes = response.content

    reader = PdfReader(io.BytesIO(content_bytes))
    page_count = len(reader.pages)

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    content = "\n\n".join(pages).strip()

    if not content:
        raise ValueError(f"No text could be extracted from {url}")

    logger.info(
        "document_parsed_pypdf",
        url=url,
        page_count=page_count,
        content_length=len(content),
    )

    return ParsedDocument(content=content, page_count=page_count, source_url=url)


async def parse_document_from_bytes(
    file_bytes: bytes,
    filename: str = "document.pdf",
    source_url: str = "",
) -> ParsedDocument:
    """Parse a PDF from uploaded bytes.
    
    Saves to a temporary file, parses with Docling,
    then cleans up. Falls back to pypdf if Docling fails.
    
    Args:
        file_bytes: Raw PDF bytes from file upload.
        filename: Original filename for logging.
        source_url: Optional source URL for metadata.
        
    Returns:
        ParsedDocument with extracted text and metadata.
    """
    import tempfile
    import os

    logger.info("parsing_document_from_bytes", filename=filename)

    # Try Docling first
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False

        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            result = converter.convert(tmp_path)
            content = result.document.export_to_markdown()
            page_count = len(result.document.pages)
        finally:
            os.unlink(tmp_path)

        logger.info(
            "document_parsed_docling",
            filename=filename,
            page_count=page_count,
            content_length=len(content),
        )
        return ParsedDocument(
            content=content,
            page_count=page_count,
            source_url=source_url or filename,
        )

    except Exception as e:
        logger.warning("docling_bytes_parser_failed", filename=filename, error=str(e))
        return await parse_pdf_bytes_with_pypdf(file_bytes, filename, source_url)


async def parse_pdf_bytes_with_pypdf(
    file_bytes: bytes,
    filename: str = "document.pdf",
    source_url: str = "",
) -> ParsedDocument:
    """Fallback PDF parsing from bytes using pypdf."""
    import io
    logger.info("parsing_bytes_pypdf", filename=filename)

    reader = PdfReader(io.BytesIO(file_bytes))
    page_count = len(reader.pages)

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    content = "\n\n".join(pages).strip()

    if not content:
        raise ValueError(f"No text could be extracted from {filename}")

    logger.info(
        "document_parsed_pypdf_bytes",
        filename=filename,
        page_count=page_count,
        content_length=len(content),
    )

    return ParsedDocument(
        content=content,
        page_count=page_count,
        source_url=source_url or filename,
    )