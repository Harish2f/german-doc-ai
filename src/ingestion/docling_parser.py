import httpx
from dataclasses import dataclass
from docling.document_converter import DocumentConverter
from src.logger import get_logger
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption

logger = get_logger(__name__)

@dataclass
class ParsedDocument:
    """Result of parsing a PDF document with docling.
    
    Contains the extracted text content and metadata
    needed to create a Document and DocumentRecord.
    """
    content:str
    page_count:int
    source_url:str


async def parse_document_from_url(url:str) -> ParsedDocument:
    """Download and parse a PDF from a URL using docling.
    
    Docling handles complex layouts, tables, footnotes,
    and German special characters automatically.

    Args:
        url: public URL of the PDF to parse.

    Returns:
        ParsedDocument with extracted text and metadata.

    Raises:
        ValueError:If the URL cannot be fetched or parsed.
    """
    logger.info("parsing_document",url=url)

    try:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False # OCR not required for digital files, also faster.
        
        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options = pipeline_options
                )
            }
        )
        result = converter.convert(url)

        content = result.document.export_to_markdown()
        page_count=len(result.document.pages)

        logger.info(
            "document_parsed",
            url=url,
            page_count=page_count,
            content_length=len(content)
            )
        return ParsedDocument(
            content=content,
            page_count=page_count,
            source_url=url,
        )

    except Exception as e:
        logger.error("document_parsing_failed", url=url, error=str(e))
        raise ValueError(f"Failed to parse document from {url}: {str(e)}")